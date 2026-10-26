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
└── media/               # photos and scans (MEDIA_ROOT)
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

What goes into `media/` and how it comes out again is [Photos and scans](#photos-and-scans), below.

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

- `/login/` and `/logout/` are Django's `LoginView` and `LogoutView`, wired in `apps/common/urls.py`
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
`/media/`, which is `apps.common.views.media.media_view`; there is no `static()` for media and no web
server pointing at `MEDIA_ROOT`. A guessed URL gets the login page, a path that leads out of the media
directory - `../`, a symlink - gets a 404. So does any file of a kind the upload never makes: only JPEG,
PNG, WebP, TIFF and PDF are handed out, with a fixed content type, so an `.html` or `.svg` that reached the
directory some other way cannot run as a page of Zweigerl.

Behind nginx (#37), `ZWEIGERL_MEDIA_ACCEL_PREFIX` names an `internal` nginx location mapped to
`MEDIA_ROOT`, e.g. `/_media/`. The view still checks the login, then answers with an empty body and
`X-Accel-Redirect` - the path percent-encoded, since nginx reads it as a URI - and nginx sends the bytes.
Unset, Django sends the file itself.

**Every upload goes through `apps.common.media.store_upload`** - the files on a source (#15), photos (#16)
and the pictures a PAF import brings (#24) alike. A `FileField` saved any other way - a plain model form,
the admin - writes the file under its original name with everything in it, so the ticket that adds a file
field routes it through `store_upload`, and a review finds it when it does not.

- **Stored where the layout below puts it**, under the name the caller passes without its extension -
  `store_upload(uploaded_file=…, name="photos/17/original")` - and one extension per kind: `jpg`, `png`,
  `webp`, `tif`, `pdf`, whatever the upload was called. Storing at a name again replaces the file there,
  also one of another kind; the storage is set to `allow_overwrite`, since Django would otherwise keep the
  old file and put the new one beside it under a random suffix. The original name is dropped and kept
  nowhere: "Taufe Josef Huber 1931.jpg" says who is in the picture.
- **Accepted:** JPEG (also the camera kind with previews, MPO), PNG, WebP, TIFF and PDF, by extension and
  by content. Anything else, a file whose content does not match its extension, and a scan with several
  pages or an animation - only the first frame would survive - raise `UploadRefusedError` with a German
  message for the form. HEIC from phones is not accepted yet (#49).
- **An image keeps the picture and nothing about it but two facts:** the date it was taken - which #16
  shows - and its orientation, plus the colour profile. Everything else is dropped rather than picked
  out: GPS, camera and lens, serial numbers, the photographer's name, descriptions, copyright, comments,
  XMP. Whatever a phone or a program writes there next may name a person or a place. A JPEG keeps its
  quantisation tables, so it is not visibly recompressed; one with previews is saved at quality 95.
- **A TIFF is turned upright and keeps no tags:** Pillow writes no EXIF sub-blocks into a TIFF, so the
  orientation is applied to the pixels and the date taken does not survive. A scan rarely has one.
- **A PDF keeps its pages and nothing else** (#50). It is written again from what each page shows -
  content, resources, size, rotation - with `pypdf`, and everything around it stays behind: the document
  information (author, title, subject, keywords, creator, producer and both dates), XMP and an editor's
  private data on the document, on its pages and on anything they draw - pictures, forms, fonts -,
  bookmarks, form fields, page labels, embedded files and scripts. The creation date goes too: for a scan
  it is the day of the scanning, not of the certificate. A comment or a mark-up on a page stays, without
  its author and date; a file attachment, a sound, a movie or a link does not. A PDF `pypdf` cannot read,
  and an encrypted one, raise `UploadRefusedError` rather than being kept as they came. Pictures inside a
  PDF are not checked for EXIF of their own.

### The layout

**The media directory is ordered by the row a file belongs to, and named from ids and roles - never from
a name.** Anyone holding the data directory finds every file of a photo or a source from its id in the
database or the export, without Zweigerl.

```
media/
├── photos/<photo-id>/original.<ext>     # what was uploaded; a file derived from it sits beside it, named for its role
└── sources/<source-id>/<file-id>.<ext>  # the scans and PDFs of one source
```

- **No folder per person.** A group photo belongs to several people; who is on a photo is the database's
  to say, and the export sorts by person.
- **No name, date or place in a path.** A path ends up in logs, in URLs, in the browser history and in the
  file list of a backup (#39), and a name that changes - corrected, or after a wedding - would have to move
  files. The GEDCOM export (#26) names the files by these paths too; readable names are for the export that
  packs the files with it (#36), from the data as it is then.
- **Paths are English**: `photos`, `sources`, `original`.
- **A path can be guessed from an id**, which is harmless while everyone logged in sees the whole family.
  A ticket that hides people from some accounts has to check that in `media_view` too. A replaced file
  keeps its URL, so the view answers `Cache-Control: private, no-cache` and the browser never shows the old
  picture.
- The layout lives here and in the callers in `apps.family_tree`, not in `store_upload`: `apps.common` knows
  no photos and no sources. An action that adds such a file writes its row first, so the id exists, and
  stores the file inside the same transaction - a refused upload then leaves no row behind.

### When a file goes

**A file goes with its row, and only once the row is gone for good** (#72). The action that deletes a source,
one of its files or a photo deletes the rows first and hands the file names to
`apps.common.media.delete_on_commit`, which deletes them in `transaction.on_commit`: a rollback keeps the rows
and their files together, and a committed deletion leaves no file nobody sees - nor one `media_view` would
still hand out under its old URL. The directory `sources/<id>/` or `photos/<id>/` stays behind empty.

- **Every deletion of such a row goes through its action** - `delete_source`, `delete_source_file`,
  `delete_photo` - the admin's too: `SourceAdmin` and `PhotoAdmin` override `delete_model` and
  `delete_queryset`. There is no `post_delete` signal; no cascade reaches a file's row without one of these
  actions, since deleting a person takes neither their sources nor their photos. A ticket that adds such a
  cascade adds the files to its action as well.
- **Photos and sources outlive the people they belong to** (decided 18.10.2026 for sources in #19, 19.10.2026
  for photos in #72). Deleting a person takes their facts and their links, and the question before it says
  what stays. A photo or a source that then belongs to nobody is on no card any more and is reachable only in
  the admin, where it can be deleted. A photo is deleted *only* there; the person card has no "Foto löschen".

## Backups

**`manage.py backup` and "Jetzt sichern" on the settings page write one consistent copy of everything a person
entered into a new folder** (#27, #33), in the backup folder of the settings - `InstallationSettings.backup_dir` - or, for
the command, in the one `--target` names, an external disk for instance:

```
<backup folder>/
└── 2026-10-19_143012/       # local time, to the second
    ├── zweigerl.sqlite3     # the database, through VACUUM INTO
    ├── zweigerl.sql         # the same state as SQL text, readable without SQLite
    ├── gedcom/              # the GEDCOM export of each tree, see gedcom.md
    │   ├── 1-familie-huber.ged    # "<id>-<name>", so two trees never share a file (#34)
    │   └── 2-familie-berger.ged
    └── media/               # the media directory as it is
```

- **A copy, not a file copied while the app writes.** `VACUUM INTO` writes a consistent database even while
  the app keeps running, which a copy of `zweigerl.sqlite3` with its `-wal` and `-shm` beside it is not. The
  SQL dump is read from that copy, so both say the same.
- **A folder, not a zip** (decided 18.10.2026, #27): unchanged media can become hardlinks to the previous
  backup (#40), restic or a synced vault only move what changed (#39), and a single photo opens without
  Zweigerl. One file to take along is an export, the `.gedzip` of #36.
- **Never half a backup.** The folder is written as `<stamp>.incomplete/` and renamed once everything is in
  it. A folder with that suffix is never a backup, and the next run names any it finds. It deletes none of
  them, and no old backup: a backup deletes nothing.
- **Refused, with a German message**, when no folder is set, when it does not exist - a disk that is not
  plugged in must not become an empty folder in its place - when it lies inside the data directory or the
  repository, or cannot be written. `actions.backup.check_backup_dir` holds these checks, and the settings page
  runs the same ones before it keeps a folder, storing it as an absolute path.
- `actions.backup.create_backup` does the work, and the command and the button call exactly it. It takes the
  GEDCOM text from its caller, since an action does not call a reader, and has to run outside a transaction:
  SQLite refuses `VACUUM` inside one. The button runs it within the request.
- **"Zuletzt gesichert" is the moment of the last finished backup**, wherever it went: `create_backup` stores
  it as `InstallationSettings.last_backup_at` once the folder has its final name, so a half-written one never counts
  and one on a `--target` disk does. The sidebar says it in local calendar days - "heute", "gestern", "vor 3
  Tagen", "noch nie" - and from seven days on, or when there has never been one, adds a `brick` label
  "Sicherung fällig" leading to the button. It is read from the database, not from the folder, so a page
  never waits on a disk.

## Running it

Run the development server as it starts, on **127.0.0.1**. `runserver 0.0.0.0` puts the family on the
local network, behind nothing but a password. Hosting Zweigerl for others is its own ticket (#37).

## Test data

Test data is always invented — see [test data](testing-data.md). That includes the smoke database of the
browser run and anything pasted into an issue.

## Related

- Serving media only to someone logged in: #21
- Backups: the command #27 and the button #33, see [Backups](#backups); off-site: #39; on a schedule: #41
