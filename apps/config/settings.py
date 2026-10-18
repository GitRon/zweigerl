"""
Django settings for Zweigerl.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import importlib.util
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Moves into the environment, together with the database and the media, when the family data leaves
# the repository (#3).
SECRET_KEY = "django-insecure-zweigerl-only-for-local-development-replaced-in-3"

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
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

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
# Moves out of the repository into the data directory with #3.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


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
