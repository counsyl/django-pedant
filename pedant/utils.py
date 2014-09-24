from django.template import Template
from django.template.loader import render_to_string
from django.test import TestCase

from pedant.decorators import fail_on_template_errors


class PedanticTemplate(Template):
    """
    Template which will fail if it encounters errors covered by this library.
    """
    @fail_on_template_errors
    def render(self, context):
        return super(PedanticTemplate, self).render(context)


@fail_on_template_errors
def render_to_string_pedantically(*args, **kwargs):
    """
    Like render_to_string, but raises more errors.
    """
    return render_to_string(*args, **kwargs)


class PedanticTestCaseMixin(object):
    """
    Mixin that runs all tests in a TestCase with pedantic rendering.
    """
    @fail_on_template_errors
    def run(self, *args, **kwargs):
        super(PedanticTestCaseMixin, self).run(*args, **kwargs)


class PedanticTestCase(PedanticTestCaseMixin, TestCase):
    """
    Django TestCase that runs all tests with pedantic rendering.
    """
