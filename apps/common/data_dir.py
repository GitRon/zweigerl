"""
Where the family data lives: a directory outside the repository, named by the environment.

See docs/patterns/data-storage.md.
"""

from collections.abc import Mapping
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

ENVIRONMENT_VARIABLE = "ZWEIGERL_DATA_DIR"


def data_dir_from_environment(*, environ: Mapping[str, str], repo_root: Path) -> Path:
    """
    The data directory "ZWEIGERL_DATA_DIR" names, refused unless it exists and lies outside the repository.

    It is not created here: a typo in the path would otherwise start an empty family tree next to the real
    one without a word.
    """
    value = environ.get(ENVIRONMENT_VARIABLE, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"{ENVIRONMENT_VARIABLE} is not set. Name a directory outside the repository in .env, "
            f"see docs/contributing/setup.md."
        )

    data_dir = Path(value).expanduser().resolve()
    if not data_dir.exists():
        raise ImproperlyConfigured(f"{ENVIRONMENT_VARIABLE} names {data_dir}, which does not exist. Create it first.")
    if not data_dir.is_dir():
        raise ImproperlyConfigured(f"{ENVIRONMENT_VARIABLE} names {data_dir}, which is not a directory.")
    if data_dir.is_relative_to(repo_root.resolve()):
        raise ImproperlyConfigured(
            f"{ENVIRONMENT_VARIABLE} names {data_dir}, which lies inside the repository. The family data must "
            f"never be where git can pick it up - see docs/patterns/data-storage.md."
        )

    return data_dir
