"""
Settings used when running the test suite.
"""

import os
import tempfile

# The suite runs without a ".env": a data directory of its own, outside the repository, and a key that
# protects nothing. "setdefault", so a developer's environment is not overridden - but the database the
# tests use is pytest-django's own, never the one in the data directory.
os.environ.setdefault("ZWEIGERL_DATA_DIR", tempfile.mkdtemp(prefix="zweigerl-tests-"))
os.environ.setdefault("DJANGO_SECRET_KEY", "zweigerl-tests-only")

from apps.config.settings import *

# Tests don't need a secure (and therefore slow) hasher
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
