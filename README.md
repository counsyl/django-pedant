# django-pedant

Make Django templates fail fast on a variety of errors.

<img src="vote_pedant.jpg" alt="This image is slightly off center."/>
<br><sub>Source: [Flickr:karen_od](https://www.flickr.com/photos/karen_od/33199)</sub>

It's happened to all of us. We forget a template variable in a context, or
have a bug in a property accessed in a template. Django, a battle-forged web
framework, was designed to **serve the damn webpage no matter what**, much to
the chagrin of web developers who have found easily fixable bugs going unfixed
for months. It's the worst. It's literally like getting stabbed in the back and left to
bleed out, muttering "Et tu, Django?" with your last breaths. *Literally.* It's
that bad.

Enter django-pedant, the pedantic template renderer's friend.

## What is this package pedantic about?
I think you mean "about what is this package pedantic?" Seriously, though, Django
is very lenient in at least the following ways:
- Exceptions raised in computing `{% if expression %}` expressions other builtin tags.
  In general, errors in custom tags are allowed to propagate.
- `KeyError` and `AttributeError` in `{{ context_variable }}` expressions.
- `UnicodeDecodeError` is caught in some places and replaced with `''` (TODO)
- In evaluating `{{ expr|filter }}` expressions, `FilterExpression.resolve` has
  `ignore_failures=True` in some case, which swallows `VariableDoesNotExist` errors.

## Usage

To decorate your view which might hide template failures, simply do:
```python
from pedant.decorators import fail_on_template_errors

@fail_on_template_errors
def my_view(request):
    # [...]
    return render_to_string('foo.html')
```

If there are errors in `foo.html`, the view will now raise a `PedanticTemplateRenderingError`
if there were any errors in rendering the template that Django swallows.

To simply *log* if there are template failures, you can use the `log_on_template_errors` decorator:
```python
import logging

from pedant.decorators import log_on_template_errors

logger = logging.getLogger('myapp.views')

@log_on_template_errors(logger, log_level=logging.INFO)
def my_view(request):
    # [...]
    return render_to_string('foo.html')
```
This will log template errors to the `myapp.views` logger at `INFO`. The default log level
is `logging.ERROR`.

For using pedantic rendering in your view tests, you can simply inherit from `PedanticTestCase`:
```python
from django.template import Template, Context
from pedant.utils import PedanticTestCase

class TestBuggyTemplate(PedanticTestCase):
    def test(self):
        Template('{{ foo }}').render(Context({'bar': 'baz'}))
```
That test will fail since `foo` is undefined in the template. `PedanticTestCase` inherits from
the standard Django `TestCase`. `PedanticTestCaseMixin` is also provided if you don't want to
incur the transactional overhead of Django's test case (e.g. for unit tests).


## Test

```sh
$ tox
```
