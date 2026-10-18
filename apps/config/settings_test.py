"""
Settings used when running the test suite.
"""

import os
import tempfile
from pathlib import Path

# The suite brings its own data directory and key, so it needs no ".env" - and set unconditionally, not as
# a default: a developer who exports ZWEIGERL_DATA_DIR for the app must never have the suite write into the
# real family data. One fixed directory in the system temp, outside the repository, reused by every run.
TEST_DATA_DIR = Path(tempfile.gettempdir()) / "zweigerl-tests"
TEST_DATA_DIR.mkdir(exist_ok=True)
os.environ["ZWEIGERL_DATA_DIR"] = str(TEST_DATA_DIR)
os.environ["DJANGO_SECRET_KEY"] = "zweigerl-tests-only"

from apps.config.settings import *

# Tests don't need a secure (and therefore slow) hasher
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
