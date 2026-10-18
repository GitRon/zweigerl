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

What goes into `medien/` and how it comes out again is [Photos and scans](#photos-and-scans), below.

## The secret key

`DJANGO_SECRET_KEY` comes from the environment too, and a missing one stops the start. It signs the
session cookies, so a key that sits in the repository lets anyone who has read the repository forge a
login.

## Where the variables come from

`apps/config/settings.py` loads `.env` from the project root with python-dotenv. `.env` is in
`.gitignore`; `.env.example` is the committed template. A variable set in the shell wins over the file.
The test settings and the smoke settings set both variables themselves before the base settings read
them - unconditionally, so an exported `ZWEIGERL_DATA_DIR` can never point a test or a smoke run at the
real family data. Neither the suite nor the browser run of `/implement-story` needs a `.env` — see
[settings](../contributing/settings.md).

A relative `ZWEIGERL_DATA_DIR` is read from the project root, where `.env` sits, not from wherever
`manage.py` was started.

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
| `AXES_RESET_ON_SUCCESS` | `True` | a successful login deletes the failed attempts before it: three wrong passwords *in a row* lock, and nothing about them is kept afterwards |
| `AXES_DISABLE_ACCESS_LOG` | `True` | no record of successful logins - who logged in when, with which browser - is written at all |

What axes still keeps, and only while it matters: an open failed attempt carries the username, the
browser's user-agent string and the page, until a successful login or `manage.py axes_reset` removes it.
axes has no setting to leave the user agent out.

`axes.W006` asks for `ip_address` in the lockout parameters; it is silenced, because with no address
handed over that parameter would put every attempt into one bucket. A locked-out login answers with HTTP
429 and `common/login_lockout.html`. `manage.py axes_reset` lifts every lockout.

## Photos and scans

**A media file is handed out by one view, behind the login, and by nothing else.** `MEDIA_URL` is
`/medien/`, which is `apps.common.views.media.media_view`; there is no `static()` for media and no web
server pointing at `MEDIA_ROOT`. A guessed URL gets the login page, a path that leads out of the media
directory - `../`, a symlink - gets a 404. So does any file of a kind the upload never makes: only JPEG,
PNG, WebP, TIFF and PDF are handed out, with a fixed content type, so an `.html` or `.svg` that reached the
directory some other way cannot run as a page of Zweigerl.

Behind nginx (#37), `ZWEIGERL_MEDIA_ACCEL_PREFIX` names an `internal` nginx location mapped to
`MEDIA_ROOT`, e.g. `/_medien/`. The view still checks the login, then answers with an empty body and
`X-Accel-Redirect` - the path percent-encoded, since nginx reads it as a URI - and nginx sends the bytes.
Unset, Django sends the file itself.

**Every upload goes through `apps.common.media.store_upload`** - the files on a source (#15), photos (#16)
and the pictures a PAF import brings (#24) alike. A `FileField` saved any other way - a plain model form,
the admin - writes the file under its original name with everything in it, so the ticket that adds a file
field routes it through `store_upload`, and a review finds it when it does not.

- **Stored under a random name** in `MEDIA_ROOT/<folder>/`, e.g. `fotos/3f2a….jpg`. The original name is
  dropped and kept nowhere: "Taufe Josef Huber 1931.jpg" says who is in the picture.
- **Accepted:** JPEG, PNG, WebP, TIFF and PDF, by extension and by content. Anything else, or a file whose
  content does not match its extension, raises `UploadRefusedError` with a German message for the form. HEIC
  from phones is not accepted yet.
- **Images lose where and with what they were taken:** the GPS block, and the camera's make, model,
  serial numbers, lens, owner name, software and maker note. XMP and comments are not carried over either.
  **The date taken stays** - it is what #16 shows - and so does the orientation and the colour profile. A
  JPEG keeps its quantisation tables, so it is not visibly recompressed.
- **A TIFF is turned upright and keeps no tags:** Pillow writes no EXIF sub-blocks into a TIFF, so the
  orientation is applied to the pixels and the date taken does not survive. A scan rarely has one.
- **A PDF is stored as it came.** Its own metadata - author, producer - is not touched yet.

## Running it

Run the development server as it starts, on **127.0.0.1**. `runserver 0.0.0.0` puts the family on the
local network, behind nothing but a password. Hosting Zweigerl for others is its own ticket (#37).

## Test data

Test data is always invented — see [test data](testing-data.md). That includes the smoke database of the
browser run and anything pasted into an issue.

## Related

- Serving media only to someone logged in: #21
- Backups of the data directory: #27, #33; off-site: #39
