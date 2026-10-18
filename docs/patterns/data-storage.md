# Data storage and privacy

**Real family data never goes into the repository.** Not the database, not a scan, not a photo, not a
name in a fixture, a test, an example or an issue. Zweigerl holds data about living relatives, and a
repository is copied, pushed and forked.

## The data directory

Everything a person enters lives in one directory **outside the repository**, named by
`ZWEIGERL_DATA_DIR`:

```
<ZWEIGERL_DATA_DIR>/
├── zweigerl.sqlite3     # the database
└── medien/              # photos and scans (MEDIA_ROOT)
```

`apps.common.data_dir.data_dir_from_environment` reads the variable when the settings load, and Zweigerl
refuses to start when:

| The variable… | Because |
|---|---|
| is missing or blank | there is no sensible default: any default would be a place nobody chose |
| names a path that does not exist | it is not created automatically - a typo would otherwise start an empty family tree beside the real one, without a word |
| names a file | the database and the media need a directory |
| names a directory **inside the repository** | that is exactly where git can pick the data up; `.gitignore` is a second line of defence, not the first |

**Put the directory in an encrypted area** — an encrypted volume, a FileVault/BitLocker disk, a
Cryptomator vault. A stolen laptop should not hand over the family.

`MEDIA_ROOT` is set, but nothing serves it yet: a URL anyone could guess must not reach a photo, and the
view that checks the login before handing out a file is #21.

## The secret key

`DJANGO_SECRET_KEY` comes from the environment too, and a missing one stops the start. It signs the
session cookies, so a key that sits in the repository lets anyone who has read the repository forge a
login.

## Where the variables come from

`apps/config/settings.py` loads `.env` from the project root with python-dotenv. `.env` is in
`.gitignore`; `.env.example` is the committed template. A variable set in the shell wins over the file.
The test settings and the smoke settings set both variables themselves before the base settings read
them, so neither the suite nor the browser run of `/implement-story` needs a `.env` — see
[settings](../contributing/settings.md).

## The login

Every page sits behind `LoginRequiredMiddleware`, locally too. A view that has to be reachable without a
login says so with `login_not_required`; Django's own login view already does.

- `/anmelden/` and `/abmelden/` are Django's `LoginView` and `LogoutView`, wired in `apps/common/urls.py`
  with the templates in `apps/common/templates/common/`. Logging out is a POST.
- Accounts are made with `manage.py createsuperuser`; there is no sign-up.

## Guessed passwords: django-axes

| Setting | Value | Why |
|---|---|---|
| `AXES_FAILURE_LIMIT` | 3 | three wrong passwords lock the account |
| `AXES_COOLOFF_TIME` | 15 minutes | then it opens again by itself |
| `AXES_LOCKOUT_PARAMETERS` | `["username"]` | the same name from another address is still locked; another name from the same address is not |
| `AXES_CLIENT_IP_CALLABLE` | `apps.common.axes.no_client_ip` | returns `None`, so no IP address is ever stored - lockouts go by username and the address would be personal data kept for nothing |

`axes.W006` asks for `ip_address` in the lockout parameters; it is silenced, because with no address
handed over that parameter would put every attempt into one bucket. A locked-out login answers with HTTP
429 and `common/login_lockout.html`. `manage.py axes_reset` lifts every lockout.

## Running it

Run the development server as it starts, on **127.0.0.1**. `runserver 0.0.0.0` puts the family on the
local network, behind nothing but a password. Hosting Zweigerl for others is its own ticket (#37).

## Test data

Test data is always invented — see [test data](testing-data.md). That includes the smoke database of the
browser run and anything pasted into an issue.

## Related

- Serving media only to someone logged in: #21
- Backups of the data directory: #27, #33; off-site: #39
