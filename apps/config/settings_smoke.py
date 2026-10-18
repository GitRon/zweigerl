"""
Settings used when a browser drives the app for a content review, see the "/implement-story" skill.

Deliberately the application settings, not a stripped-down variant: a content review is only worth its
wall-clock if the app under the browser behaves like the real one. What changes is where the data goes -
a throwaway database and a throwaway data directory - and the secret key, so a smoke run can never touch
the real family data and needs no ".env".
"""

import os
import tempfile
from pathlib import Path

# content-server.sh names both: the database inside the run directory, the data directory outside the
# repository, where the data directory check accepts it. Set unconditionally, not as a default, so an
# exported ZWEIGERL_DATA_DIR cannot point a smoke run at the real data. By hand, without either, both go
# into one fresh temporary directory.
SMOKE_DATA_DIR = Path(os.environ.get("SMOKE_DATA_DIR") or tempfile.mkdtemp(prefix="zweigerl-smoke-"))
os.environ["ZWEIGERL_DATA_DIR"] = str(SMOKE_DATA_DIR)
os.environ["DJANGO_SECRET_KEY"] = "zweigerl-smoke-only"

from apps.config.settings import *
from apps.config.settings import DATABASES

DATABASES = {
    "default": {
        **DATABASES["default"],
        "NAME": Path(os.environ.get("SMOKE_DB_PATH", SMOKE_DATA_DIR / "smoke.sqlite3")),
    }
}
