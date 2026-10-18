# Zweigerl

Ein Stammbaum, in dem jede Angabe ihren Beleg hat.

A Django 6.1 app on Python 3.14 with a SQLite database. Pages are server-rendered and move with
[datastar](https://data-star.dev); components are [django-cotton](https://django-cotton.com).

```bash
uv sync && yarn install && yarn build:css
cp .env.example .env                     # then name a data directory outside the repo and set a key
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver        # 127.0.0.1 only
```

The details are in [local setup](docs/contributing/setup.md).

## Documentation

**This list is the index of every doc.** Each doc is normative for the area it covers and holds its topic
once; a doc that is not listed here does not exist. Read the relevant one before working in that area
rather than inferring the conventions from nearby code.

### Getting started

- [Agent guide](AGENTS.md) — which doc to read before touching what
- [Local setup](docs/contributing/setup.md) — stack, dependencies, the stylesheet, running the app, the
  suite and CI
- [Linting](docs/contributing/linting.md) — ruff, boa-restrictor and its `ZBR` rules, import-linter,
  complexipy, pre-commit
- [Settings](docs/contributing/settings.md) — the settings modules and the environment they read,
  templates, static files, locale and which language goes where, logging
- [Commit messages](docs/contributing/commit-messages.md) — and the `#<n>: ` that starts a pull request's title

### Architecture

- [Where code goes](docs/patterns/app-layout.md) — the two apps, actions and readers instead of a message
  bus, business rules as database constraints, and what has to sit at the app root
- [Data storage and privacy](docs/patterns/data-storage.md) — no real family data in the repository, the
  data directory outside it, the login and the lockout
- [Persons and families](docs/patterns/family.md) — `Person`, `Partnership`, `ParentChild` and `SiblingPair` after
  GEDCOM, derived siblings, the home person, the Familie Huber fixture
- [Belege](docs/patterns/evidence.md) — facts, sources and citations, reliability, "unbelegt", uncertain
  dates *(scaffold, #8)*
- [datastar](docs/patterns/datastar.md) — the pinned version, signals, fragments, pages, CSRF, toasts and
  when JavaScript of our own is allowed
- [Template components](docs/patterns/components.md) — a reused or patched template is a cotton
  component: where it lives, its parameters, slots, and the `id` datastar morphs on
- [Responsive layout](docs/patterns/responsive-layout.md) — the desk is the default, what a narrow
  window still gets, and why the phone waits for `v2`
- [Visual identity](docs/patterns/visual-identity.md) — the colours, typefaces and building blocks from
  the moodboard: what each colour may be spent on, the word mark, the frame, labels and buttons

### Testing

- [Testing strategy](docs/patterns/testing-strategy.md) — what to test, at which level
- [Test conventions](docs/patterns/testing-conventions.md) — layout, naming, assertions
- [Test data](docs/patterns/testing-data.md) — invented data only, factories and fixtures
- [Mocking](docs/patterns/mocking.md) — first-party mocks are a review finding
- [Coverage](docs/patterns/coverage.md) — the 100% branch gate
- [Architecture tests](docs/patterns/architecture-tests.md) — the whole-tree tests, and the rule each one
  holds

### Planning

- [Writing an issue](docs/collaboration/writing-issues.md) — labels, anatomy in German, and the review
  pass before an issue is created
