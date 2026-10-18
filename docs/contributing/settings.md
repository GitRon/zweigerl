# Settings

- `apps/config/settings.py` — the application settings. It reads `.env` from the project root and refuses
  to start without `ZWEIGERL_DATA_DIR` and `DJANGO_SECRET_KEY` - see
  [data storage](../patterns/data-storage.md).
- `apps/config/settings_test.py` — the test settings, pointed at by `[tool.pytest.ini_options]` in
  `pyproject.toml`. It sets both variables - unconditionally, never to the real data directory - to
  `zweigerl-tests` in the system temp and a throwaway key before the base settings read them, so the suite
  needs no `.env`, and swaps the password hasher for a fast one.
- `apps/config/settings_smoke.py` — used when a browser drives the app for the content review of
  [`/implement-story`](../../.claude/skills/implement-story/SKILL.md). Identical to the application
  settings except for where the data goes: the database comes from `SMOKE_DB_PATH`, the data directory
  from `SMOKE_DATA_DIR` (a temporary directory outside the repository that `content-server.sh` makes per
  run), and the key is a throwaway. Nothing else is relaxed: a content review is only worth its
  wall-clock if the app under the browser is the real one.

Where the database, the media and the secret key come from is the subject of
[data storage](../patterns/data-storage.md).

## Templates

The template loaders are written out instead of `APP_DIRS`, because the cotton loader has to run first,
and `django_cotton.apps.SimpleAppConfig` is installed instead of `django_cotton`, because the default one
rewrites `TEMPLATES` in its `ready()` — see [template components](../patterns/components.md#configuration).

`apps.common.context_processors.toasts` is the one context processor of our own. It hands the layout a
callable rather than a list, so that only the layout takes the toasts out of the session — see
[datastar](../patterns/datastar.md#toasts).

## Static files

`STATICFILES_DIRS` is `static/` and nothing else: the compiled stylesheet in `static/dist/` and the
vendored datastar bundle in `static/vendor/`. Nothing is loaded from a CDN, so the app keeps working with
the network unplugged.

## Locale

`LANGUAGE_CODE = "de-at"` and `TIME_ZONE = "Europe/Vienna"`. The interface is German, so are model and
field names where a person reads them, and the docs and code comments are English.

## Logging

One console handler, on the root logger, at `WARNING`. Two things about the dict are deliberate rather
than stylistic:

- **The `django` logger is listed with no handlers of its own.** Django applies its own configuration
  first and gives that logger a console handler without turning propagation off, so leaving it out would
  print every Django record twice — once there, once on the root handler. Listing it hands its records to
  the one console handler. It also drops `mail_admins` from that chain; the project configures neither
  `ADMINS` nor a mail backend.
- **The loggers below it come along.** `logging.config` resets every existing logger under a configured
  one, so naming `django` leaves `django.server` and `django.request` with no handler of their own and
  propagation on. The runserver request lines therefore arrive in the project's format, timestamped and
  named, rather than in Django's `[server_time] message`.
