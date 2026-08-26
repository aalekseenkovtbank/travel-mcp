#!/usr/bin/env python3
"""Regression test: login must use the controlling TTY after npx detaches stdin."""

from __future__ import annotations

import errno
import os
import pathlib
import pty
import select
import signal
import sys
import tempfile
import time


PHONE_PROMPT = b"FAKE_PHONE:"
OTP_PROMPT = b"FAKE_OTP:"
EXPECTED = b"CAPTURED:+79990000000|424242"
FORCE_REINSTALL = b"FORCE_REINSTALL"


def _fake_python(path: pathlib.Path) -> None:
    path.write_text(
        """#!/bin/sh
if [ "${1:-}" = "-m" ] && [ "${2:-}" = "pip" ]; then
  case " $* " in
    *" --force-reinstall "*)
      case " $* " in
        *" --no-deps "*) printf 'FORCE_REINSTALL\\n' ;;
      esac
      ;;
  esac
  exit 0
fi
printf 'FAKE_PHONE:'
if ! IFS= read -r phone; then
  printf 'PHONE_EOF\\n'
  exit 31
fi
printf 'FAKE_OTP:'
if ! IFS= read -r otp; then
  printf 'OTP_EOF\\n'
  exit 32
fi
printf 'CAPTURED:%s|%s\\n' "$phone" "$otp"
""",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _read_until_exit(pid: int, master: int, timeout: float = 20.0) -> tuple[int, bytes]:
    output = bytearray()
    phone_sent = False
    otp_sent = False
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        readable, _, _ = select.select([master], [], [], 0.1)
        if readable:
            try:
                chunk = os.read(master, 4096)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                chunk = b""
            output.extend(chunk)
            if PHONE_PROMPT in output and not phone_sent:
                os.write(master, b"+79990000000\n")
                phone_sent = True
            if OTP_PROMPT in output and not otp_sent:
                os.write(master, b"424242\n")
                otp_sent = True

        waited, status = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return os.waitstatus_to_exitcode(status), bytes(output)

    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    raise AssertionError(f"interactive login timed out; output={bytes(output)!r}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test-interactive-login.py <launcher>")
    launcher = os.path.abspath(sys.argv[1])

    with tempfile.TemporaryDirectory(prefix="travel-mcp-tty-") as temp:
        data_home = pathlib.Path(temp) / "data"
        fake = data_home / "tbank-mcp" / "travel-venv" / "bin" / "python"
        fake.parent.mkdir(parents=True)
        _fake_python(fake)

        env = os.environ.copy()
        env["XDG_DATA_HOME"] = str(data_home)

        pid, master = pty.fork()
        if pid == 0:
            # Keep the PTY as the controlling terminal but reproduce npm/npx
            # handing the launcher an already-consumed stdin.
            devnull = os.open(os.devnull, os.O_RDONLY)
            os.dup2(devnull, 0)
            os.close(devnull)
            os.execve(launcher, [launcher, "login"], env)

        try:
            exit_code, output = _read_until_exit(pid, master)
        finally:
            os.close(master)

    if exit_code != 0 or EXPECTED not in output or FORCE_REINSTALL not in output:
        raise AssertionError(
            "launcher did not recover interactive input and force-refresh its "
            f"vendored Python: exit={exit_code}, output={output!r}"
        )
    print("Travel MCP interactive login TTY: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
