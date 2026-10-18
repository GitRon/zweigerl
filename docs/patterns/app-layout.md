# Where code goes

**There are two Django apps: `apps.stammbaum`, which is the domain, and `apps.common`, which is not.** A
Django app is a unit of persistence and Django configuration — models, migrations, templates, template
tags, fixtures, admin — and not a unit of code organisation.

Everything in the app layer sits directly under `apps/`, so that directory lists the whole architecture:

```
apps/
├── config/                      # the settings package, deliberately not an app
├── common/                      # a satellite: layout, toasts, datastar helpers; imports no domain code
└── stammbaum/                   # the domain app
    ├── urls.py
    ├── actions/                 # everything that writes
    ├── readers/                 # everything that reads
    ├── views/                   # the web interface, one module per screen
    ├── templates/stammbaum/     # pages
    ├── templates/cotton/<topic>/  # components
    └── tests/                   # mirrors the tree above
```

## Business logic: actions and readers

**Business logic has two places, and a view is neither.** There is no message bus. Writes and reads are
plain functions, the way Fabian's [django-datastar](https://github.com/fbinz/django-datastar) example
splits them:

| Package | Holds | May call |
|---|---|---|
| `actions/` | Everything that writes: one function per thing a person does, keyword arguments in, the changed rows out | models |
| `readers/` | Everything that reads: the queries a screen needs, returning rows or plain values | models |
| `views/` | Reads the request, calls actions and readers, renders a page or answers with datastar events | actions, readers |

- **A view never builds a query or writes a row itself.** If a view needs `objects.filter()`, that query
  is a reader. If it calls `save()`, that write is an action.
- **An action never calls a reader, and a reader never writes.** An action that needs to look something
  up does so on the model directly; a reader that would need to write is two functions.
- **One module per subject**, named after what it is about: `actions/person.py`, `readers/person.py`.
- Every function takes **keyword-only arguments**, which boa-restrictor enforces outside views.

The layers contract in `pyproject.toml` fails the build when an import goes the wrong way — see
[linting](../contributing/linting.md#import-boundaries).

What has no database behind it — the German name of a relationship, the layout of the tree, parsing
"um 1931" — is a pure function in a module named after its subject (`verwandtschaft.py`, `baum.py`),
called by readers or views and tested without the database. The ticket that introduces the first one
adds its package here.

## Rules in the database

**A rule the data must always satisfy lives in the database, as a constraint, wherever the database can
express it.** An action or a form checks it too, to give the person a good message; the constraint is what
holds when something writes past them - the admin, the shell, an import, the next action somebody adds. A
rule kept only in Python is a rule that holds until the first write path that forgot it.

What goes into the model's `Meta.constraints` and field options:

| Rule | As | Example |
|---|---|---|
| A value is required | `null=False`, no `blank` | a person has a family name |
| A value is one of a set | `CheckConstraint` on the choices - Django does not add one | the reliability is *belegt*, *wahrscheinlich* or *überliefert* |
| Fields depend on each other | `CheckConstraint` | a second date exists only for "between" |
| A row is not its own relative | `CheckConstraint` comparing two columns | nobody is their own parent |
| Something exists once | `UniqueConstraint`, with `condition` where it holds only for some rows | one partnership per pair of people |
| A row must not vanish while others point at it | `on_delete=PROTECT` or `RESTRICT` instead of `CASCADE` | a source still cited by a fact |

What the database cannot express stays in the action, with its own test: rules across several rows or
tables, such as no person being their own ancestor three generations up, and anything derived - *unbelegt*
is computed, not stored, see [Belege](belege.md).

- **Name every constraint** `<model>_<rule>`, e.g. `person_not_own_parent`, so a failure says what broke.
- **Give it a German `violation_error_message`.** Model validation (`full_clean`, and with it every
  `ModelForm`) checks constraints too and shows that message, so the rule is written once.
- **A model with constraints inherits `ValidateConstraintsOnSaveMixin`** from
  [ambient-toolbox](https://pypi.org/project/ambient-toolbox/), first in its bases:
  `class Person(ValidateConstraintsOnSaveMixin, models.Model)`. Its `save()` runs `clean()` and
  `validate_constraints()` before writing, so a forbidden row raises `ValidationError` with that German
  message on every path that saves - an action, the shell, an import - and not only behind a form. The
  constraint in the database still holds whatever bypasses `save()`: `bulk_create()`, `QuerySet.update()`
  and two writes racing each other end in `IntegrityError`. The mixin costs one query per constraint and
  save; an import that writes thousands of rows weighs that against `bulk_create()`.
- **Uniqueness is a `UniqueConstraint`, never `unique=True` or `unique_together`.** The mixin validates
  `Meta.constraints` only; the other two would be left to the database and its bare `IntegrityError`.
- **Every constraint ships with its migration**, and a constraint added to a table that already has rows
  comes with a data migration that makes them comply first - otherwise `migrate` fails on the real data.
- **Test each constraint twice**: once through `save()`, which the mixin answers with `ValidationError`,
  and once past it, which only the database can refuse - see [testing strategy](testing-strategy.md#levels).
  A model change without its migration fails the suite, see
  [architecture tests](architecture-tests.md).

## The app root is Django's

Django looks exactly one fixed path into an app for each of the things it discovers, and never below it.
These live at the app root and nowhere else — putting one anywhere deeper makes it vanish with no error:

| At the app root | Because Django reads only |
|---|---|
| `migrations/` | `<app>/migrations/` |
| `models/__init__.py` | `<app>/models` — a model missing from it gets no table |
| `templates/` | `<app>/templates/` — pages under `<app>/templates/<app>/`, components under `cotton/`, see [components](components.md) |
| `templatetags/` | `<app>/templatetags/` |
| `management/commands/` | `<app>/management/commands/` |
| `fixtures/` | `<app>/fixtures/` |
| `admin.py` | `<app>/admin.py` |
| `apps.py`, `urls.py` | named from settings and the root urlconf |

## apps.common

`apps.common` holds what does not know about families: the page layout and toast components, the toast
helpers, the datastar helpers, the toast context processor. It never imports `apps.stammbaum`; the
import-linter contract fails the build when it does. Something that needs a person, a source or a
relationship belongs in `apps.stammbaum`, however general it looks.
