"""
Add ifdef expression to allow for optionally including a variable in a render
context. Based on the implementation from http://stackoverflow.com/a/21922810
"""
import re

from django.template import Library
from django.template import TemplateSyntaxError
from django.template.defaulttags import IfNode
from django.template.smartif import IfParser, Literal

register = Library()


class IfDefLiteral(Literal):
    def eval(self, context):
        vars = self.value.split('.')
        defined = vars[0] in context
        if not defined:
            return False
        evaluated = context[vars[0]]
        for attr in vars[1:]:
            if hasattr(evaluated, attr):
                evaluated = getattr(evaluated, attr)
            else:
                return False
        return defined


# Based on http://stackoverflow.com/a/10134719 This regexp will identify all
# identifier1.identifier2.identifier3 sequences.
PYTHON_IDENTIFIER_REGEXP = re.compile(r'^([^\d\W]\w*[.]?)+\Z')


class IfDefParser(IfParser):
    def create_var(self, value):
        if not PYTHON_IDENTIFIER_REGEXP.match(value):
            raise TemplateSyntaxError('%r is not an identifier.' % value)
        return IfDefLiteral(value)


@register.tag
def ifdef(parser, token):
    """
    Check if variable is defined in the context.

    Similar to django.template.defaulttags.do_if.
    """
    block_tokens = ('elifdef', 'else', 'endifdef')
    # {% ifdef ... %}
    bits = token.split_contents()[1:]
    if len(bits) > 1:
        raise TemplateSyntaxError('%r is not an identifier.' % token)
    condition = IfDefParser(bits).parse()
    nodelist = parser.parse(block_tokens)
    conditions_nodelists = [(condition, nodelist)]
    token = parser.next_token()

    # {% elifdef ... %} (repeatable)
    while token.contents.startswith('elifdef'):
        bits = token.split_contents()[1:]
        if len(bits) > 1:
            raise TemplateSyntaxError('%r is not an identifier.' % token)
        condition = IfDefParser(bits).parse()
        nodelist = parser.parse(block_tokens)
        conditions_nodelists.append((condition, nodelist))
        token = parser.next_token()

    # {% else %} (optional)
    if token.contents == 'else':
        nodelist = parser.parse(block_tokens[-1:])
        conditions_nodelists.append((None, nodelist))
        token = parser.next_token()

    # {% endifdef %}
    assert token.contents == 'endifdef'

    return IfNode(conditions_nodelists)
