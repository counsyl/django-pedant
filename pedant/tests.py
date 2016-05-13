import logging
from unittest import skipIf

import django
from django.conf import settings
from django.template import Library
from django.template.base import Context
from django.template.base import FilterExpression
from django.template.base import Template
from django.template.base import TemplateSyntaxError
from django.test import TestCase
from django.test.utils import override_settings
from mock import Mock
from mock import patch

from pedant.decorators import _fail_template_string_if_invalid
from pedant.decorators import strict_resolve
from pedant.decorators import _log_template_string_if_invalid
from pedant.decorators import fail_on_template_errors
from pedant.decorators import log_template_errors
from pedant.decorators import patch_string_if_invalid
from pedant.decorators import PedanticTemplateRenderingError
from pedant.utils import PedanticTemplate
from pedant.utils import PedanticTestCase
from pedant.utils import PedanticTestCaseMixin


def patch_builtins(library):
    if django.VERSION < (1, 9):
        return patch('django.template.base.builtins', [library])
    else:
        from django.template.engine import Engine
        engine = Engine.get_default()
        return patch.object(engine, 'template_builtins', [library])


class TestMissingVariable(TestCase):
    template = Template('before{{ a }}after')
    success_context = Context({'a': '|'})
    failure_context = Context({})

    @patch_string_if_invalid(' invalid ')
    def test_log_base_decorator_failure_template_string(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'before invalid after')

    @patch_string_if_invalid(' invalid %s ')
    def test_log_base_decorator_failure_format_template_string(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'before invalid a after')

    @patch_string_if_invalid('')
    def test_log_base_decorator_failure_empty_template_string(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'beforeafter')

    def test_log_base_decorator_success(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.success_context)

        result = render()
        self.assertFalse(logger.log.called, result)
        self.assertEqual(result, 'before|after')

    def test_log_decorator_failure(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'beforeafter')

    def test_log_decorator_success(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.success_context)

        result = render()
        self.assertFalse(logger.log.called, result)
        self.assertEqual(result, 'before|after')

    def test_fail_base_decorator_failure(self):
        @_fail_template_string_if_invalid
        def render():
            return self.template.render(self.failure_context)

        with self.assertRaises(PedanticTemplateRenderingError) as assertion:
            render()
        self.assertEqual(
            str(assertion.exception),
            u"Unknown template variable <Variable: u'a'>")

    def test_fail_base_decorator_success(self):
        @_fail_template_string_if_invalid
        def render():
            return self.template.render(self.success_context)

        self.assertEqual(render(), 'before|after')

    def test_fail_decorator_failure(self):
        @fail_on_template_errors
        def render():
            return self.template.render(self.failure_context)

        with self.assertRaises(PedanticTemplateRenderingError) as assertion:
            render()
        self.assertEqual(
            str(assertion.exception),
            u"Unknown template variable <Variable: u'a'>")


class TestCustomTagsAndFilters(TestCase):
    """
    Test that custom-defined template tags and filters already fail in django.

    If this test fails in future versions of django, the decorators will need
    to be updated, but at the moment, no action is required.
    """

    def test_custom_template_tag_already_fails_without_decorator(self):
        register = Library()

        class FailError(AttributeError):
            pass

        @register.simple_tag(name='fail_tag')
        def fail_tag():
            raise FailError()

        with patch_builtins(register):
            with self.assertRaises(FailError):
                Template('{% fail_tag %}').render(Context())

    def test_custom_filter_already_fails_without_decorator(self):
        register = Library()

        class FailError(AttributeError):
            pass

        @register.filter(name='fail_filter')
        def fail_filter(arg):
            raise FailError()

        with patch_builtins(register):
            with self.assertRaises(FailError):
                Template('{{ ""|fail_filter }}').render(Context())


class TestMissingKey(TestCase):
    template = Template('before{{ a.b }}after')
    success_context = Context({'a': {'b': '|'}})
    failure_context = Context({'a': {}})

    def test_log_base_decorator_failure(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called)
        self.assertEqual(result, 'beforeafter')

    def test_log_base_decorator_success(self):
        logger = Mock()

        @_log_template_string_if_invalid(logger, logging.ERROR)
        def render():
            return self.template.render(self.success_context)

        result = render()
        self.assertFalse(logger.log.called, result)
        self.assertEqual(result, 'before|after')

    def test_log_decorator_failure(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'beforeafter')

    def test_log_decorator_success(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.success_context)

        result = render()
        self.assertFalse(logger.log.called, result)
        self.assertEqual(result, 'before|after')

    def test_fail_base_decorator_failure(self):
        @_fail_template_string_if_invalid
        def render():
            return self.template.render(self.failure_context)

        with self.assertRaises(PedanticTemplateRenderingError) as assertion:
            render()
        self.assertEqual(
            str(assertion.exception),
            u"Unknown template variable <Variable: u'a.b'>")

    def test_fail_base_decorator_success(self):
        @_fail_template_string_if_invalid
        def render():
            return self.template.render(self.success_context)

        self.assertEqual(render(), 'before|after')

    def test_fail_decorator_failure(self):
        @fail_on_template_errors
        def render():
            return self.template.render(self.failure_context)

        with self.assertRaises(PedanticTemplateRenderingError) as assertion:
            render()
        self.assertEqual(
            str(assertion.exception),
            u"Unknown template variable <Variable: u'a.b'>")


class TestAttributeError(TestCase):
    template = Template('before{% if a.b %}|{% endif %}after')

    class WithAttribute(object):
        b = True

    class WithoutAttribute(object):
        pass

    success_context = Context({'a': WithAttribute})
    failure_context = Context({'a': WithoutAttribute})

    def test_log_decorator_failure(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.failure_context)

        result = render()
        self.assertTrue(logger.log.called, result)
        self.assertEqual(result, 'beforeafter')

    def test_log_decorator_success(self):
        logger = Mock()

        @log_template_errors(logger, logging.ERROR)
        def render():
            return self.template.render(self.success_context)

        result = render()
        self.assertFalse(logger.log.called, result)
        self.assertEqual(result, 'before|after')

    def test_fail_decorator_failure(self):
        @fail_on_template_errors
        def render():
            return self.template.render(self.failure_context)

        with self.assertRaises(PedanticTemplateRenderingError):
            render()


class TestUnicodeDecodeError(TestCase):
    def test_fail_on_unicode_decode_error(self):
        register = Library()

        @register.filter(name='fail_filter')
        def fail_filter(arg):
            return '%s\x99' % u'\xa9'

        with self.assertRaises(UnicodeDecodeError):
            fail_filter('')

        with patch_builtins(register):
            template = Template('{{ a|fail_filter }}')

            @fail_on_template_errors
            def render():
                return template.render(Context({'a': ''}))

            self.assertEqual(template.render(Context({'a': ''})), '')
            with self.assertRaises(UnicodeDecodeError):
                render()

    @override_settings(DEBUG=False, TEMPLATE_DEBUG=False)
    def test_log_on_unicode_decode_error(self):
        register = Library()

        @register.filter(name='fail_filter')
        def fail_filter(arg):
            return '%s\x99' % u'\xa9'

        logger = Mock()

        with patch_builtins(register):
            template = Template('{{ a|fail_filter }}')

            @log_template_errors(logger, logging.ERROR)
            def render():
                return template.render(Context({'a': ''}))

            self.assertEqual(template.render(Context({'a': ''})), '')
            self.assertFalse(logger.log.called)
            render()
            self.assertTrue(logger.log.called)

    @override_settings(DEBUG=True, TEMPLATE_DEBUG=True)
    def test_log_on_unicode_decode_error_debug(self):
        register = Library()

        @register.filter(name='fail_filter')
        def fail_filter(arg):
            return '%s\x99' % u'\xa9'

        logger = Mock()

        with patch_builtins(register):
            template = Template('{{ a|fail_filter }}')

            @log_template_errors(logger, logging.ERROR)
            def render():
                return template.render(Context({'a': ''}))

            self.assertEqual(template.render(Context({'a': ''})), '')
            self.assertFalse(logger.log.called)
            render()
            self.assertTrue(logger.log.called)


class TestForWith(TestCase):
    for_template = Template('{% for i in foo %}{{ i }}{% endfor %}')
    with_template = Template('{% with bar=foo %}{{ bar }}{% endwith %}')
    nested_with_template = Template(
        '{% with bar=foo %}{% with baz=bar %}{{ baz }}{% endwith %}{% endwith %}')  # nopep8

    def _test_template_success(self, template, context, expected):
        self.assertEqual(template.render(context), expected)

        @fail_on_template_errors
        def render_strictly():
            return template.render(context)

        self.assertEqual(render_strictly(), expected)
        logger = Mock()

        @log_template_errors(logger)
        def render_log():
            return template.render(context)

        render_log()
        self.assertFalse(logger.log.called)

    def _test_template_failure(self, template):
        context = Context()
        self.assertEqual(template.render(context), '')

        @fail_on_template_errors
        def render_strictly():
            return template.render(context)

        with self.assertRaises(PedanticTemplateRenderingError):
            render_strictly()

        logger = Mock()

        @log_template_errors(logger)
        def render_log():
            return template.render(context)

        render_log()
        self.assertTrue(logger.log.called)

    def test_for_failure(self):
        self._test_template_failure(self.for_template)

    def test_for_success(self):
        context = Context({'foo': ['a', 'b']})
        expected = 'ab'
        self._test_template_success(self.for_template, context, expected)

    def test_with_failure(self):
        self._test_template_failure(self.with_template)

    def test_with_success(self):
        context = Context({'foo': 'foo'})
        expected = 'foo'
        self._test_template_success(self.with_template, context, expected)

    def test_nested_with_failure(self):
        self._test_template_failure(self.nested_with_template)

    def test_nested_with_success(self):
        context = Context({'foo': 'foo'})
        expected = 'foo'
        self._test_template_success(
            self.nested_with_template, context, expected)


class TestLogDecorator(TestCase):
    def test_nested(self):
        """
        Test that when log decorators are nested, log is only called once.
        """
        template = Template('{{ a }}')
        logger1 = Mock()
        logger2 = Mock()

        @log_template_errors(logger2)
        def render2():

            @log_template_errors(logger1)
            def render1():
                template.render(Context())

            return render1()

        render2()
        self.assertTrue(logger1.log.called)
        self.assertFalse(logger2.log.called)

    @patch_string_if_invalid('WTF is %s?')
    def test_template_string_if_invalid_is_respected(self):
        """
        Test log decorators include the original string_if_invalid.
        """
        template = Template('{{ a }}')
        original_render = template.render(Context())
        self.assertEqual(original_render, 'WTF is a?')
        logger = Mock()

        @log_template_errors(logger)
        def render():
            return template.render(Context())

        logged_render = render()
        self.assertTrue(logger.log.called)
        self.assertEqual(logged_render, original_render)

    @patch_string_if_invalid('WTF is %s?')
    def test_nested_calls_respect_template_string_if_invalid(self):
        """
        Test log decorators include the original string_if_invalid.
        """
        template = Template('{{ a }}')
        original_render = template.render(Context())
        self.assertEqual(original_render, 'WTF is a?')
        logger1 = Mock()
        logger2 = Mock()

        @log_template_errors(logger2)
        def render2():

            @log_template_errors(logger1)
            def render1():
                return template.render(Context())

            return render1()

        logged_render = render2()
        self.assertTrue(logger1.log.called)
        self.assertFalse(logger2.log.called)
        self.assertEqual(logged_render, original_render)

    @skipIf(django.VERSION >= (1, 8), 'Not an issue as of Django 1.8')
    @patch_string_if_invalid('Fixed String')
    def test_render_incorrect_template(self):
        """
        Handle weird django behavior.

        Django caches an invalid_var_format_string at the top level of the
        module. So if TEMPLATE_STRING_IF_INVALID is '', it will never actually
        call LogInvalidVariableTemplate.__mod__ if it failed to render a
        template before (in the same process) while *not* in the context of
        a log decorator.
        """

        with patch('django.template.base.invalid_var_format_string', None), \
                patch.object(FilterExpression, 'resolve', strict_resolve):
            logger = Mock()

            template = Template('{{ a }}')
            template.render(Context())
            from django.template import base
            self.assertFalse(base.invalid_var_format_string)

            @log_template_errors(logger)
            def render():
                return template.render(Context())
            render()

        self.assertTrue(logger.log.called)

    @skipIf(django.VERSION >= (1, 8), 'Not an issue as of Django 1.8')
    @patch_string_if_invalid('Fixed String')
    def test_contains_behavior(self):
        logger = Mock()

        @log_template_errors(logger)
        def render():
            with patch('django.template.base.invalid_var_format_string', None):
                return Template('{{ a }}').render(Context())

        render()
        self.assertTrue(logger.log.called)

    def test_invalid_log_levels(self):
        logger = Mock
        with self.assertRaises(ValueError):
            @log_template_errors(logger, -10)
            def invalid_level_int():
                pass

        with self.assertRaises(ValueError):
            @log_template_errors(logger, 'error')
            def invalid_level_non_int():
                pass


class TestPedanticTemplate(TestCase):
    @skipIf(django.VERSION >= (1, 8), 'Not an issue as of Django 1.8')
    @override_settings(TEMPLATE_STRING_IF_INVALID='Fixed String')
    def test_render_incorrect_template(self):
        with patch('django.template.base.invalid_var_format_string', None), \
                patch.object(FilterExpression, 'resolve', strict_resolve):
            template = Template('{{ a }}')
            template.render(Context())
            from django.template import base
            self.assertFalse(base.invalid_var_format_string)

            with self.assertRaises(PedanticTemplateRenderingError):
                PedanticTemplate('{{ a }}').render(Context())
            PedanticTemplate('{{ a }}').render(Context({'a': 'a'}))

    @skipIf(django.VERSION >= (1, 8), 'Not an issue as of Django 1.8')
    @override_settings(TEMPLATE_STRING_IF_INVALID='Fixed String')
    def test_contains_behavior(self):
        @fail_on_template_errors
        def render():
            with patch('django.template.base.invalid_var_format_string', None):
                return Template('{{ a }}').render(Context())

        with self.assertRaises(PedanticTemplateRenderingError):
            render()


class TestPedanticTestCase(PedanticTestCase):
    def test(self):
        """
        Since this class inherits from PedanticTestCase, rendering should
        fail.
        """
        with self.assertRaises(PedanticTemplateRenderingError):
            Template('{{ a }}').render(Context())
        # Rendering a correct context should still succeed.
        Template('{{ a }}').render(Context({'a': 'a'}))


class TestPedanticTestCaseMixin(PedanticTestCaseMixin, TestCase):
    def test(self):
        """
        Since this class inherits from PedanticTestCaseMixin, rendering
        should fail.
        """
        with self.assertRaises(PedanticTemplateRenderingError):
            Template('{{ a }}').render(Context())
        # Rendering a correct context should still succeed.
        Template('{{ a }}').render(Context({'a': 'a'}))


class TestDefaultFilter(PedanticTestCase):
    def test_default_filter_fails_if_undefined(self):
        # TODO: this might not be the most desirable behavior. Ideally we'd
        # monkeypatch the default filter to not fail if the variable is
        # undefined.
        self.assertEqual(
            Template('{{ a|default:"foo"}}').render(Context({'a': 'bar'})),
            'bar'
        )
        with self.assertRaises(PedanticTemplateRenderingError):
            Template('{{ a|default:"foo" }}').render(Context())


class TestIfDefTags(PedanticTestCase):
    def test_ifdef(self):
        ifdef_template = Template(
            """{% load pedant_tags %}
              {% ifdef a %}
                  {{ a }} is defined.
              {% elifdef b %}
                  {{ b }} is defined.
              {% else %}
                  Neither a nor b is defined.
              {% endifdef %}""")
        self.assertEqual(
            'a is defined.',
            ifdef_template.render(Context({'a': 'a'})).strip())
        self.assertEqual(
            'b is defined.',
            ifdef_template.render(Context({'b': 'b'})).strip())
        self.assertEqual(
            'Neither a nor b is defined.',
            ifdef_template.render(Context()).strip())

    def test_ifdef_body_still_fails_for_undefined_variables(self):
        ifdef_template = Template(
            "{% load pedant_tags %}\n{% ifdef a %}{{ b }}{% endifdef %}")
        self.assertEqual(
            ifdef_template.render(Context({'a': 'a', 'b': 'b'})).strip(),
            'b')
        with self.assertRaises(PedanticTemplateRenderingError):
            ifdef_template.render(Context({'a': 'a'}))

    def test_ifdef_disallows_non_identifier_expressions(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                "{% load pedant_tags %}\n{% ifdef a and b %}{% endifdef %}")

    def test_ifdef_disallows_non_identifier_expressions_2(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                "{% load pedant_tags %}\n{% ifdef a|filter %}{% endifdef %}")

    def test_elifdef_disallows_non_identifier_expressions(self):
        with self.assertRaises(TemplateSyntaxError):
            Template(
                "{% load pedant_tags %}\n{% ifdef a %}{% elifdef a and b %}{% endifdef %}")

    def test_ifdef_follows_attributes(self):
        ifdef_template = Template(
            "{% load pedant_tags %}\n"
            "{% ifdef a.b.c %}defined{% else %}undefined{% endifdef %}")

        class Foo(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        self.assertEqual(
            ifdef_template.render(Context({'a': Foo()})).strip(),
            'undefined')
        self.assertEqual(
            ifdef_template.render(Context({'a': Foo(b=Foo())})).strip(),
            'undefined')
        self.assertEqual(
            ifdef_template.render(Context({'a': Foo(b=Foo(c=Foo()))})).strip(),
            'defined')
