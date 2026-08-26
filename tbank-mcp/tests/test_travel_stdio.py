"""Real MCP initialize + tools/list against the travel stdio entrypoint."""
import json
import os
import select
import shlex
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_COUNT = 33


def read_response(process, wanted_id, timeout=75):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([process.stdout], [], [], 1)
        if not ready:
            if process.poll() is not None:
                raise AssertionError(
                    f"server exited {process.returncode}: {process.stderr.read()}")
            continue
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                raise AssertionError(
                    f"server exited {process.returncode}: {process.stderr.read()}")
            continue
        payload = json.loads(line)
        if payload.get("id") == wanted_id:
            return payload
    raise AssertionError(f"MCP response {wanted_id} timed out")


def send(process, payload):
    process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
    process.stdin.flush()


def test_stdio_handshake_and_tools_list():
    env = dict(os.environ)
    # The dedicated entrypoint must override a hostile inherited value.
    env["TBANK_TOOLSET"] = "all"
    env["TBANK_TRACE"] = "0"
    command = shlex.split(os.environ.get("TRAVEL_STDIO_COMMAND", "")) or [
        sys.executable, "-m", "src.travel_server"]
    timeout = int(os.environ.get("TRAVEL_STDIO_TIMEOUT", "75"))
    process = subprocess.Popen(
        command, cwd=ROOT, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1)
    try:
        send(process, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "travel-packaging-test", "version": "1"},
            },
        })
        initialized = read_response(process, 1, timeout=timeout)
        assert "result" in initialized and initialized["result"]["serverInfo"]["name"] == "tbank-travel"
        send(process, {
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        })
        send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listed = read_response(process, 2, timeout=timeout)["result"]["tools"]
        assert len(listed) == EXPECTED_COUNT
        assert {tool["name"] for tool in listed} >= {
            "nearby_search", "weather", "hotel_search", "train_stations", "train_search",
            "compare_flight_prices", "compare_train_prices", "compare_hotel_prices",
            "compare_flight_hotel_prices"}
        assert not ({"login", "transfer", "train_calendar", "get_data"} &
                    {tool["name"] for tool in listed})
        for tool in listed:
            assert tool["annotations"]["readOnlyHint"] is True
            assert tool["annotations"]["destructiveHint"] is False
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    test_stdio_handshake_and_tools_list()
    print("travel stdio: initialize + tools/list OK")
