import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.common.data_dir import data_dir_from_environment


def test_data_dir_from_environment_returns_the_directory(tmp_path):
    repo_root = tmp_path / "zweigerl"
    data_dir = tmp_path / "daten"
    data_dir.mkdir()

    result = data_dir_from_environment(environ={"ZWEIGERL_DATA_DIR": str(data_dir)}, repo_root=repo_root)

    assert result == data_dir.resolve()


def test_data_dir_from_environment_reads_a_relative_path_from_the_repository(tmp_path):
    repo_root = tmp_path / "zweigerl"
    repo_root.mkdir()
    data_dir = tmp_path / "daten"
    data_dir.mkdir()

    result = data_dir_from_environment(environ={"ZWEIGERL_DATA_DIR": "../daten"}, repo_root=repo_root)

    assert result == data_dir.resolve()


def test_data_dir_from_environment_refuses_a_missing_variable(tmp_path):
    with pytest.raises(ImproperlyConfigured, match="ZWEIGERL_DATA_DIR is not set"):
        data_dir_from_environment(environ={}, repo_root=tmp_path)


def test_data_dir_from_environment_refuses_a_blank_variable(tmp_path):
    with pytest.raises(ImproperlyConfigured, match="ZWEIGERL_DATA_DIR is not set"):
        data_dir_from_environment(environ={"ZWEIGERL_DATA_DIR": "  "}, repo_root=tmp_path)


def test_data_dir_from_environment_refuses_a_directory_that_does_not_exist(tmp_path):
    with pytest.raises(ImproperlyConfigured, match="which does not exist"):
        data_dir_from_environment(
            environ={"ZWEIGERL_DATA_DIR": str(tmp_path / "vertippt")}, repo_root=tmp_path / "zweigerl"
        )


def test_data_dir_from_environment_refuses_a_file(tmp_path):
    data_file = tmp_path / "daten.txt"
    data_file.write_text("")

    with pytest.raises(ImproperlyConfigured, match="which is not a directory"):
        data_dir_from_environment(environ={"ZWEIGERL_DATA_DIR": str(data_file)}, repo_root=tmp_path / "zweigerl")


def test_data_dir_from_environment_refuses_a_directory_inside_the_repository(tmp_path):
    data_dir = tmp_path / "daten"
    data_dir.mkdir()

    with pytest.raises(ImproperlyConfigured, match="lies inside the repository"):
        data_dir_from_environment(environ={"ZWEIGERL_DATA_DIR": str(data_dir)}, repo_root=tmp_path)
