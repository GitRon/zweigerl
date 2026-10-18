# Agent guide

Zweigerl is a Django app for a family tree in which every fact carries its source. It is set up like
[Tettenhall](https://github.com/GitRon/tettenhall), without the message bus.

**[README.md](README.md) indexes every doc.** It is the map — there is deliberately no second list here to
drift out of step with it.

The docs are normative for the areas they cover, not background reading. Read the relevant one *before*
touching that area, and do not infer the conventions from whatever code happens to be nearby.

| Before you… | Read |
|---|---|
| add a model, an action, a reader, a view, a template or a component | [Where code goes](#where-code-goes), below |
| add or change anything datastar does: signals, fragments, toasts, a page answering both ways | [datastar](docs/patterns/datastar.md) |

**Real family data never goes into the repository** — not in fixtures, not in tests, not in an example.
Test data is invented.

## Where code goes

**There are two Django apps.** `apps.stammbaum` is the whole domain, `apps.common` is its satellite for
what does not know about families: the layout, toasts, the datastar helpers. `apps.common` never imports
`apps.stammbaum`; import-linter enforces it.

**Business logic has two places, and a view is neither.** As in Fabian's
[django-datastar](https://github.com/fbinz/django-datastar) example:

| Package | Holds | Calls |
|---|---|---|
| `apps/stammbaum/actions/` | Everything that writes: one function per thing a person does, keyword arguments in, the changed rows out | models |
| `apps/stammbaum/readers/` | Everything that reads: the queries a screen needs | models |
| `apps/stammbaum/views/` | Reads the request, calls actions and readers, renders a page or answers with datastar events | actions, readers |

A view never builds a query or writes a row itself. An action never calls a reader or a view, a reader
never writes. The layers contract in `pyproject.toml` fails the build when an import goes the wrong way.

**Django discovers by fixed paths at the app root.** Models, templates, template tags, fixtures, admin
registrations and management commands go where Django looks for them, in the app root, or they never
load — with no error anywhere. Templates live in `<app>/templates/<app>/`, components in
`<app>/templates/cotton/<topic>/`.
