import argparse
import json
import os
import subprocess
import sys

import pytest

from mcp_tailwindplus import FRAMEWORK_CHOICES, _project_setting
from mcp_tailwindplus.tailwind_plus import Framework


def _run_cli(*args, env=None):
    """Run the CLI entry point in a subprocess and capture its output."""
    return subprocess.run(
        [sys.executable, "-c", "from mcp_tailwindplus import main; main()", *args],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
    )


@pytest.fixture
def old_downloader_data_file(tmp_path):
    """A valid JSON data file whose downloader version is too old, so constructing
    TailwindPlus raises inside main()'s try/except."""
    path = tmp_path / "old-data.json"
    path.write_text(
        json.dumps(
            {
                "version": "x",
                "downloaded_at": "x",
                "component_count": 0,
                "download_duration": "x",
                "downloader_version": "2.0.0",
                "tailwindplus": {},
            }
        )
    )
    return str(path)


def test_startup_error_is_concise_without_debug(old_downloader_data_file):
    """Without --debug, a startup failure prints a one-line message, no traceback."""
    result = _run_cli("--tailwindplus-data", old_downloader_data_file)

    assert result.returncode == 1
    assert "Error starting server" in result.stderr
    assert "downloader version" in result.stderr
    assert "Traceback" not in result.stderr


def test_startup_error_prints_traceback_with_debug(old_downloader_data_file):
    """With --debug, a startup failure prints the full traceback."""
    result = _run_cli("--debug", "--tailwindplus-data", old_downloader_data_file)

    assert result.returncode == 1
    assert "Traceback" in result.stderr
    assert "ValueError" in result.stderr


def test_invalid_project_setting_option_is_rejected(old_downloader_data_file):
    result = _run_cli(
        "--tailwindplus-data", old_downloader_data_file, "--framework", "svelte"
    )

    assert result.returncode == 2
    assert "invalid choice: 'svelte'" in result.stderr


@pytest.mark.parametrize(
    ("env_name", "value"),
    [
        ("MCP_TAILWINDPLUS_FRAMEWORK", "svelte"),
        ("MCP_TAILWINDPLUS_TAILWIND_VERSION", "5"),
        ("MCP_TAILWINDPLUS_MODE", "none"),
    ],
)
def test_invalid_project_setting_environment_is_rejected(
    old_downloader_data_file, env_name, value
):
    """An invalid setting is rejected before the data file is loaded."""
    result = _run_cli(
        "--tailwindplus-data", old_downloader_data_file, env={env_name: value}
    )

    assert result.returncode == 2
    assert f"{env_name} must be one of" in result.stderr
    assert "Error starting server" not in result.stderr


class TestProjectSetting:
    """Test resolving a project setting from the command line and environment."""

    ENV_NAME = "MCP_TAILWINDPLUS_FRAMEWORK"

    def _resolve(self, cli_value):
        return _project_setting(
            argparse.ArgumentParser(),
            cli_value,
            self.ENV_NAME,
            Framework,
            FRAMEWORK_CHOICES,
        )

    def test_option(self, monkeypatch):
        monkeypatch.delenv(self.ENV_NAME, raising=False)
        assert self._resolve("react") is Framework.REACT

    def test_environment(self, monkeypatch):
        monkeypatch.setenv(self.ENV_NAME, "vue")
        assert self._resolve(None) is Framework.VUE

    def test_option_takes_precedence_over_environment(self, monkeypatch):
        monkeypatch.setenv(self.ENV_NAME, "vue")
        assert self._resolve("react") is Framework.REACT

    def test_unset(self, monkeypatch):
        monkeypatch.delenv(self.ENV_NAME, raising=False)
        assert self._resolve(None) is None
