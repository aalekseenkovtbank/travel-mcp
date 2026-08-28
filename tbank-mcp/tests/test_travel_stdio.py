"""Real MCP initialize + tools/list against the travel stdio entrypoint."""
import json
import os
import select
import shlex
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_COUNT = 41


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
            "nearby_search", "weather", "hotel_search", "hotel_rates", "hotel_reviews",
            "hotel_checkout_url",
            "hotel_search_filters", "hotel_latest_offers",
            "train_stations", "train_search",
            "compare_flight_prices", "compare_train_prices", "compare_hotel_prices",
            "compare_flight_hotel_prices"}
        assert {"trip_personalization_profile", "yandex_venue_search",
                "render_trip_page"} <= {tool["name"] for tool in listed}
        assert not ({"login", "transfer", "train_calendar", "get_data"} &
                    {tool["name"] for tool in listed})
        for tool in listed:
            if tool["name"] == "render_trip_page":
                assert tool["annotations"]["readOnlyHint"] is False
                assert tool["annotations"]["openWorldHint"] is False
            else:
                assert tool["annotations"]["readOnlyHint"] is True
            assert tool["annotations"]["destructiveHint"] is False
        by_name = {tool["name"]: tool for tool in listed}
        filters_tool = by_name["hotel_search_filters"]
        latest_tool = by_name["hotel_latest_offers"]
        assert "ВЫЗЫВАЙ" in filters_tool["description"]
        assert "hotel_filters()" in filters_tool["description"]
        assert "прямо перед" in latest_tool["description"]
        assert "price.isFinalPrice=false" in latest_tool["description"]
        assert by_name["render_trip_page"]["outputSchema"]
        assert "document" in by_name["render_trip_page"]["inputSchema"]["properties"]
        assert set(latest_tool["inputSchema"]["required"]) >= {
            "hotel_ids", "checkin_date", "checkout_date"}

        send(process, {"jsonrpc": "2.0", "id": 3, "method": "prompts/list", "params": {}})
        prompts = read_response(process, 3, timeout=timeout)["result"]["prompts"]
        by_prompt_name = {prompt["name"]: prompt for prompt in prompts}
        assert "personalized_weekend_landing" in by_prompt_name
        landing_prompt = by_prompt_name["personalized_weekend_landing"]
        assert {arg["name"] for arg in landing_prompt["arguments"]} >= {
            "city", "date_from", "date_to", "hotel_query", "adults",
            "spending_lookback_days"}

        send(process, {
            "jsonrpc": "2.0", "id": 4, "method": "prompts/get",
            "params": {
                "name": "personalized_weekend_landing",
                "arguments": {
                    "city": "Москва", "date_from": "2026-08-29",
                    "date_to": "2026-08-30", "hotel_query": "Continental",
                    "adults": "2", "spending_lookback_days": "60",
                },
            },
        })
        rendered = read_response(process, 4, timeout=timeout)["result"]
        prompt_text = "\n".join(
            message["content"].get("text", "") for message in rendered["messages"])
        assert "Москва" in prompt_text
        assert "Continental" in prompt_text
        assert "hotel_checkout_url разрешён только после явного выбора" in prompt_text
        assert "Не раскрывай" in prompt_text
        assert "render_trip_page(document)" in prompt_text
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    test_stdio_handshake_and_tools_list()
    print("travel stdio: initialize + tools/list + prompts/list + prompts/get OK")
