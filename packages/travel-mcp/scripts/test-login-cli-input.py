#!/usr/bin/env python3
"""Stdlib-only tests for the vendored login CLI input boundary."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import pathlib
import sys
import types


class FakeTbankApiError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class FakeSession:
    def __init__(self):
        self.access_token = ""
        self.mobile_sessionid = "test-session-id"
        self.calls: list[tuple[str, str]] = []

    def login(self, phone: str) -> str:
        return "otp requested"

    def confirm_step(self, step: str, value: str) -> None:
        self.calls.append((step, value))
        if step == "otp":
            self.access_token = "test-access-token"


def _load_login_cli(path: pathlib.Path, session: FakeSession):
    src = types.ModuleType("src")
    client = types.ModuleType("src.client")
    server = types.ModuleType("src.server")
    client.TbankApiError = FakeTbankApiError
    server._blank_session = lambda: session
    server._save_session = lambda value: value is session
    server._SESSION_FILE = "/tmp/test-session.json"
    server._session = None
    src.server = server

    previous = {name: sys.modules.get(name) for name in ("src", "src.client", "src.server")}
    sys.modules.update({"src": src, "src.client": client, "src.server": server})
    try:
        spec = importlib.util.spec_from_file_location("travel_login_cli_test", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test-login-cli-input.py <login_cli.py>")
    login_path = pathlib.Path(sys.argv[1])

    accepted = FakeSession()
    cli = _load_login_cli(login_path, accepted)
    cli.getpass.getpass = lambda prompt: " 424242 "
    with contextlib.redirect_stdout(io.StringIO()):
        result = cli.login("+79990000000")
    assert result == 0
    assert accepted.calls == [("otp", "424242")]

    refused = FakeSession()
    cli = _load_login_cli(login_path, refused)
    cli.getpass.getpass = lambda prompt: ""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = cli.login("+79990000000")
    assert result == 1
    assert refused.calls == []
    assert "Запрос в банк не отправлен" in output.getvalue()

    print("Travel MCP login CLI input validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
