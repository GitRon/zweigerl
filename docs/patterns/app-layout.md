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
