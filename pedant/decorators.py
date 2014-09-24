import logging

from decorator import decorator
from django.conf import settings
from django.template.base import FilterExpression
from django.template.base import VariableNode
from django.template.debug import DebugVariableNode
from django.utils.encoding import force_text
from django.utils.formats import localize
from django.utils.html import escape
from django.utils.safestring import EscapeData
from django.utils.safestring import SafeData
from django.utils.timezone import template_localtime
from mock import patch

try:
    from django.template.base import render_value_in_context
except ImportError:
    # Django 1.6+ made this a private method
    from django.template.base import _render_value_in_context as \
        render_value_in_context  # pragma: no cover


class PedanticTemplateRenderingError(Exception):
    pass


# This strategy relies on http://djangosnippets.org/snippets/646/
# and the behavior of invalid variables.
# https://docs.djangoproject.com/en/dev/ref/templates/api/#invalid-template-variables  # nopep8
class FailInvalidVariableTemplate(object):
    def __mod__(self, missing):
        """
        Raise an error instead of returning a string.

        Django has a TEMPLATE_STRING_IF_INVALID setting which it substitutes
        into a rendered document when an error is encountered.
        When django tries to format the missing variable into the string, we
        instead raise an exception.
        """
        message = 'Unknown template variable %r' % missing
        raise PedanticTemplateRenderingError(message)

    def __contains__(self, search):
        return search == '%s'


class LogInvalidVariableTemplate(object):
    def __init__(self, logger, log_level):
        template_string = settings.TEMPLATE_STRING_IF_INVALID
        if isinstance(template_string, LogInvalidVariableTemplate):
            # If there are nested decorators, use the actual *string*, not the
            # other LogInvalidVariableTemplate object, since that could lead
            # to multiple log calls for the same error.
            self.template_string = template_string.template_string
        else:
            self.template_string = template_string
        self.level = log_level
        self.logger = logger

    def __mod__(self, missing):
        """
        Log a missing variable message instead of returning a string.

        Django has a TEMPLATE_STRING_IF_INVALID setting which it substitutes
        into a rendered document when an error is encountered.
        When django tries to format the missing variable into the string, we
        instead log the error.
        """
        self.logger.log(
            self.level,
            'Unknown template variable %r', missing)

        if '%s' in self.template_string:
            return self.template_string % missing
        return self.template_string

    def __contains__(self, search):
        return search == '%s'


def _fail_template_string_if_invalid(f):
    patcher = patch.object(
        settings, 'TEMPLATE_STRING_IF_INVALID', FailInvalidVariableTemplate())
    return patcher(f)


def _log_template_string_if_invalid(logger, log_level=logging.ERROR):
    """
    Decorator to log missing variables to the specified logger.

    @_log_template_string_if_invalid(logging.getLogger('mylogger'),
                                     logging.INFO)
    def my_view(*args):
        pass

    Will log missing variables at INFO.  The default log_level is ERROR.
    """
    patcher = patch.object(
        settings,
        'TEMPLATE_STRING_IF_INVALID',
        LogInvalidVariableTemplate(logger, log_level))
    return patcher


def _patch_invalid_var_format_string(f):
    """
    Fix an issue with caching related to TEMPLATE_STRING_IF_INVALID.

    Django caches an invalid_var_format_string at the top level of the
    module. So if TEMPLATE_STRING_IF_INVALID is '', it will never actually
    call LogInvalidVariableTemplate.__mod__ if it failed to render a
    template before (in the same process) while *not* in the context of
    a log decorator.  See the implementation of
    django.template.base.FilterExpression.resolve
    """
    patcher = patch('django.template.base.invalid_var_format_string', True)
    return patcher(f)


__orig_resolve = FilterExpression.resolve


def strict_resolve(self, context, ignore_failures=False):
    """
    Resolves a ``FilterExpression`` within the context of the template.

    This patched method acts as a proxy to the original, but forces
    ``ignore_failures`` to False so that an exception is always raised when a
    variable is accessed out of scope/context.
    """
    return __orig_resolve(self, context, ignore_failures=False)


def _always_strict_resolve(f):
    return patch.object(FilterExpression, 'resolve', strict_resolve)(f)


def __apply(arg, function):
    return function(arg)


def debug_variable_node_render(self, context):
    """
    Like DebugVariableNode.render, but doesn't catch UnicodeDecodeError.
    """
    try:
        output = self.filter_expression.resolve(context)
        output = template_localtime(output, use_tz=context.use_tz)
        output = localize(output, use_l10n=context.use_l10n)
        output = force_text(output)
    except Exception as e:
        if not hasattr(e, 'django_template_source'):
            e.django_template_source = self.source
        raise
    if (context.autoescape and not isinstance(output, SafeData)) or isinstance(output, EscapeData):  # nopep8
        return escape(output)
    else:
        return output


def variable_node_render(self, context):
    """
    Like VariableNode.render, but doesn't catch UnicodeDecodeError.
    """
    output = self.filter_expression.resolve(context)
    return render_value_in_context(output, context)


def _disallow_catching_UnicodeDecodeError(f):
    """
    Patches a template modules to prevent catching UnicodeDecodeError.

    Note that this has the effect of also making Template raise a
    UnicodeDecodeError instead of a TemplateEncodingError if the template
    string is not UTF-8 or unicode.
    """
    patch_base = patch.object(VariableNode, 'render', variable_node_render)
    patch_debug = patch.object(
        DebugVariableNode, 'render', debug_variable_node_render)
    return patch_base(patch_debug(f))


def _log_unicode_errors(logger, log_level):
    """
    Catches/logs UnicodeDecodeError.
    """
    def log_debug_render(*args, **kwargs):
        try:
            return debug_variable_node_render(*args, **kwargs)
        except UnicodeDecodeError:
            logger.log(
                log_level,
                "UnicodeDecodeError in template rendering",
                exc_info=True)
        return ''

    def log_render(*args, **kwargs):
        try:
            variable_node_render(*args, **kwargs)
        except UnicodeDecodeError:
            logger.log(
                log_level,
                "UnicodeDecodeError in template rendering",
                exc_info=True)
        return ''

    patch_base = patch.object(VariableNode, 'render', log_render)
    patch_debug = patch.object(DebugVariableNode, 'render', log_debug_render)
    return lambda f: patch_base(patch_debug(f))


@decorator
def fail_on_template_errors(f, *args, **kwargs):
    """
    Decorator that causes templates to fail on template errors.
    """
    decorators = [
        _fail_template_string_if_invalid,
        _always_strict_resolve,
        _patch_invalid_var_format_string,
        _disallow_catching_UnicodeDecodeError,
    ]

    return reduce(__apply, decorators, f)(*args, **kwargs)


def log_template_errors(logger, log_level=logging.ERROR):
    """
    Decorator to log template errors to the specified logger.

    @log_template_errors(logging.getLogger('mylogger'), logging.INFO)
    def my_view(*args):
        pass

    Will log template errors at INFO.  The default log level is ERROR.
    """
    if not (isinstance(log_level, int) and
            log_level in logging._levelNames):
        raise ValueError('Invalid log level %s' % log_level)

    decorators = [
        _log_template_string_if_invalid(logger, log_level),
        _log_unicode_errors(logger, log_level),
        _always_strict_resolve,
        _patch_invalid_var_format_string,
    ]

    @decorator
    def function(f, *args, **kwargs):
        return reduce(__apply, decorators, f)(*args, **kwargs)

    return function
