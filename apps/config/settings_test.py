"""
Settings used when running the test suite.
"""

from apps.config.settings import *

# Tests don't need a secure (and therefore slow) hasher
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
