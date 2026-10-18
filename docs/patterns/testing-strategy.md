# Testing strategy

**This is the single source of truth for what to test.** Do not infer the conventions from whatever tests
happen to be nearby, and do not fall back on generic Django testing habits.

Guiding principle: **behaviour is tested where it lives.** An action is tested by calling the action, a
reader by calling the reader, and a view test only covers what the view itself decides.

## Levels

There is no target share per level: a view with five branches of its own has five tests, and a view that
only renders what a reader returns has one.

| Level | How many | What |
|---|---|---|
| Pure function | one per branch | Call it directly, no database |
| Action | one per branch | Call it directly; assert what it returns and what changed in the database |
| Reader | one per branch | Call it directly; assert what it returns |
| Constraint | two per constraint | Save the forbidden row with a factory and expect `ValidationError` with the German message - the mixin's check. Then write it past `save()` with `bulk_create()` and expect `IntegrityError`, matched on the constraint's name for a check and on its columns for a unique one - SQLite names only those - which proves the database holds it. See [rules in the database](app-layout.md#rules-in-the-database) |
| View | one, plus one per branch the view decides | Status code, context, datastar events |
| Component | per component | Render, plus one output test per behaviour — see [Components](#components) |
| Architecture | per rule | The whole tree at once — see [architecture tests](architecture-tests.md) |

## Actions

- Import and call the action **directly**, keyword arguments only: `create_person(given_names="Anna", ...)`.
- Build what it needs with [factories](testing-data.md); most action tests need `django_db`.
- At most two assertions per test: what the action returns and the database side effect.
- One test per branch: the happy path, each refusal, each edge case worth naming.

## Readers

- Call the reader directly with factory-built rows around it.
- **Include a row that must not come back.** A reader filtering by name is only tested when another name
  is in the table too.
- Assert on the returned value as a whole (`== [anna, josef]`), not on its length.

## Views

Views are thin: they read the request, call actions and readers and render. Keep the tests equally thin —
**one test per view**, plus one per branch the view itself decides (a refusal, a redirect, the datastar
answer next to the full page), via the test client, with `django_db`. A branch that lives in an action or
a reader is tested there, not through the view.

- **Page views**: assert the status code plus the one context key the view exists to provide, and the
  template with `assertTemplateUsed`.
- **datastar views**: assert the status code and the event that carries the decision — the selector a
  fragment is patched into, the signal that is set, the toast's text. Not the rendered markup of the
  fragment; that is the component's test.
- **Never assert on rendered HTML of a page.** Template assertions break on every markup change and catch
  nothing. The one exception is a defect that exists *only* in the rendered output, which in practice
  means escaping: a value interpolated into a sink that then mis-parses it. Then one test may read the
  response body, and what it asserts is the escaping, not the markup. Name the defect in the docstring and
  say the rule is being set aside on purpose.
- **The template is checked by rendering it, not by reading it.** `FAIL_INVALID_TEMPLATE_VARS` in
  `pyproject.toml` fails any test whose render reads a variable that does not resolve — which Django would
  otherwise print as nothing, the way a renamed attribute looks on the page. Two consequences:
  - **An optional value is an `{% if %}`, not a lookup that fails.**
  - **A list view's test carries at least one row.** Row markup renders only when there is a row, so a
    test on an empty list checks nothing of it.

## Components

A view's contract is its context, so its markup is incidental. A [template component](components.md) is
the other way round: what it renders *is* its contract.

| Failure | Example | Tool |
|---|---|---|
| **Render**: the component reads a variable that is not there | a parameter renamed in the component but not at its callers | A render test with every parameter, failing on an unresolved variable |
| **Logic**: a calculation gives the wrong result | which of three reliability labels applies | A unit test on the function or property — never in the template |
| **Output**: it renders, but says or does the wrong thing | a slot dropped, a wrong `@get` URL | An output test on the parsed render |

**Output tests are the scoped exception.** One may render a component on its own and read its output,
parsed with `apps/common/tests/html.py` — never string-matched. It may assert on:

- **visible text**, including slot content arriving where the caller put it,
- **behaviour attributes**: `href`, `data-on:*`, `data-signals`, `aria-*`, `role`, `disabled`, form `name`
  and `value`,
- **which branch rendered**, e.g. "unbelegt" rather than the source's title.

Not on CSS classes, element structure or order, whitespace, or a snapshot. **If a pure styling pass can
break the test, the test is wrong.** One output test per behaviour, not per component.

An output test lives at the component's mirror path:
`apps/common/templates/cotton/common/toast.html` → `apps/common/tests/templates/cotton/common/test_toast.py`.

## Don't test

- Django, datastar-py or django-cotton themselves
- Model fields and `Meta` options without logic of our own
- Admin registrations

## See also

- [Test conventions](testing-conventions.md) — layout, naming, assertions
- [Test data](testing-data.md) — factories and fixtures
- [Mocking](mocking.md)
- [Coverage](coverage.md)
- [Architecture tests](architecture-tests.md)
