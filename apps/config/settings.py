"""
Django settings for Zweigerl.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import datetime
import importlib.util
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

from apps.common.data_dir import data_dir_from_environment

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# The data directory and the secret key come from the environment, or from a ".env" in the project
# root, which git ignores. A variable set in the environment wins over the file. See
# docs/patterns/data-storage.md.
load_dotenv(BASE_DIR / ".env")

# Where the family data lives: the database and the media, outside the repository.
DATA_DIR = data_dir_from_environment(environ=os.environ, repo_root=BASE_DIR)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is not set. Put one in .env, see docs/contributing/setup.md.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # The simple config rather than "django_cotton": the default one rewrites "TEMPLATES" in its
    # "ready()", so the loaders below would not be the ones that run. This one only patches Django's
    # template lexer so a template tag inside a component attribute survives - a private Django API,
    # which is why every component is rendered in a test.
    "django_cotton.apps.SimpleAppConfig",
    # One domain app, plus a satellite for domain-independent logic. A Django app is a unit of
    # persistence and Django configuration, not of code organisation.
    "apps.stammbaum",
    "apps.common",
    "axes",
]

# A dev dependency: an install without the dev group ("uv sync --no-dev") has no such module, and the app
# would fail to load.
if DEBUG and importlib.util.find_spec("django_removals"):
    INSTALLED_APPS += ["django_removals"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Every page sits behind the login, locally too. A view that has to be reachable without one says so
    # with "login_not_required", as Django's own login view does.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # AxesMiddleware should be the last middleware in the MIDDLEWARE list.
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    # AxesBackend should be the first backend in the AUTHENTICATION_BACKENDS list.
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "common:login-view"
LOGIN_REDIRECT_URL = "stammbaum:start-view"
LOGOUT_REDIRECT_URL = "common:login-view"

ROOT_URLCONF = "apps.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        # Written out rather than "APP_DIRS": the cotton loader has to run first, compiling a "<c-...>"
        # tag into the template tags Django renders, and "APP_DIRS" cannot be combined with "loaders".
        # Templates are still found in each app's "templates/" directory and nowhere else.
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ),
            ],
            "builtins": ["django_cotton.templatetags.cotton"],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom
                "apps.common.context_processors.toasts",
            ],
        },
    },
]

WSGI_APPLICATION = "apps.config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "zweigerl.sqlite3",
    }
}

# Photos and scans, in the data directory. They are only ever handed out by "media_view", behind the
# login: MEDIA_URL points at it, and nothing serves MEDIA_ROOT directly. See docs/patterns/data-storage.md.
MEDIA_ROOT = DATA_DIR / "medien"
MEDIA_URL = "/medien/"
# Behind nginx (#37), set to the "internal" location that maps to MEDIA_ROOT, e.g. "/_medien/": the view
# then checks the login and leaves the bytes to nginx via X-Accel-Redirect. Unset, Django sends the file.
ZWEIGERL_MEDIA_ACCEL_PREFIX = os.environ.get("ZWEIGERL_MEDIA_ACCEL_PREFIX") or None


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "de-at"

TIME_ZONE = "Europe/Vienna"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = "static/"

# "static/" holds the compiled stylesheet and the vendored datastar bundle. Everything is served from
# here rather than from a CDN, so Zweigerl keeps working with the network unplugged.
STATICFILES_DIRS = (BASE_DIR / "static",)


# django-axes
# Three wrong passwords in a row lock the username out for fifteen minutes. Locked by username alone, and
# as little as possible kept: "no_client_ip" hands axes None for every request, a successful login deletes
# the failed attempts before it, and no log of successful logins is written at all.
AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = datetime.timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_CLIENT_IP_CALLABLE = "apps.common.axes.no_client_ip"
AXES_RESET_ON_SUCCESS = True
AXES_DISABLE_ACCESS_LOG = True
AXES_LOCKOUT_TEMPLATE = "common/login_lockout.html"
# axes.W006 asks for "ip_address" in AXES_LOCKOUT_PARAMETERS. With no address handed over, that parameter
# would put every attempt into one bucket instead of rate-limiting anyone.
SILENCED_SYSTEM_CHECKS = ["axes.W006"]


# Logging
# https://docs.djangoproject.com/en/stable/topics/logging/
# One console handler for the whole project, on the root logger, at WARNING. A logger of our own that
# should say more in development gets its level set below, the way "django" does.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{asctime} {levelname:<7} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        # Django gives this logger a console handler of its own without turning propagation off, so
        # leaving it alone would print every Django record twice. It keeps its level and loses its
        # handler, and every Django record reaches the console through the one handler above.
        "django": {
            "handlers": [],
            "level": "INFO" if DEBUG else "WARNING",
        },
    },
}


# Hide development server warning
# https://docs.djangoproject.com/en/stable/ref/django-admin/#envvar-DJANGO_RUNSERVER_HIDE_WARNING
# setdefault, not assignment: an operator who set the variable deliberately should win over an import
# side effect
os.environ.setdefault("DJANGO_RUNSERVER_HIDE_WARNING", "true")
