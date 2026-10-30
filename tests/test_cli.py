import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import time

import pytest

from mcp_tailwindplus import FRAMEWORK_CHOICES, _project_setting
from mcp_tailwindplus.tailwind_plus import Framework


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path, monkeypatch):
    """Keep the CLI's cache, which is in the user's cache directory, out of the
    real one, on macOS through HOME and on Linux through XDG_CACHE_HOME."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


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

    def test_empty_environment_is_unset(self, monkeypatch):
        monkeypatch.setenv(self.ENV_NAME, "")
        assert self._resolve(None) is None


@pytest.fixture
def data_file(tmp_path):
    """A small valid data file."""
    path = tmp_path / "data.json"
    snippet = {
        "code": '<div class="flex">Hello</div>',
        "language": "html",
        "mode": "light",
        "name": "html",
        "preview": "<div>Hello</div>",
        "supportsDarkMode": False,
        "version": 4,
    }
    path.write_text(
        json.dumps(
            {
                "version": "x",
                "downloaded_at": "x",
                "component_count": 1,
                "download_duration": "x",
                "downloader_version": "4.0.0",
                "tailwindplus": {
                    "Application UI": {
                        "Elements": {
                            "Badges": {
                                "Simple": {"name": "Simple", "snippets": [snippet]}
                            }
                        }
                    }
                },
            }
        )
    )
    return str(path)


def test_http_rejects_other_hosts_and_origins(data_file):
    """Over HTTP, requests naming a host other than the bind address or an
    allowed host, or a foreign browser origin, are rejected."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from mcp_tailwindplus import main; main()",
            "--tailwindplus-data",
            data_file,
            "--transport",
            "http",
            "--port",
            str(port),
            "--allowed-host",
            "*.example.net",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def status(host, origin=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        connection.putrequest("POST", "/mcp", skip_host=True)
        connection.putheader("Host", host)
        if origin:
            connection.putheader("Origin", origin)
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        ).encode()
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Accept", "application/json, text/event-stream")
        connection.putheader("Content-Length", str(len(body)))
        try:
            connection.endheaders(body)
            return connection.getresponse().status
        finally:
            connection.close()

    try:
        for _ in range(100):
            try:
                status(f"127.0.0.1:{port}")
                break
            except OSError:
                time.sleep(0.1)

        assert status(f"127.0.0.1:{port}") == 200
        assert status(f"localhost:{port}") == 200
        assert status("tunnel.example.net") == 200
        assert status("attacker.example") == 421
        assert status(f"localhost:{port}", origin="http://attacker.example") == 403
    finally:
        server.terminate()
        server.wait(timeout=10)
