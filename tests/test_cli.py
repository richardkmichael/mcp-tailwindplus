import json
import subprocess
import sys

import pytest


def _run_cli(*args):
    """Run the CLI entry point in a subprocess and capture its output."""
    return subprocess.run(
        [sys.executable, "-c", "from mcp_tailwindplus import main; main()", *args],
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
