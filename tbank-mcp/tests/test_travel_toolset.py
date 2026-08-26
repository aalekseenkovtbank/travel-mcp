"""The travel entrypoint must expose a small, physically read-only registry."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPECTED = {
    "session_status", "list_accounts", "list_operations",
    "spending_categories", "operations_histogram", "audience_profile",
    "orders", "order_details", "travel_order_details", "flight_history",
    "flight_search", "hotel_autocomplete", "hotel_search", "hotel_details",
    "hotel_filters", "compare_flight_prices", "compare_hotel_prices",
    "compare_flight_hotel_prices", "train_stations", "train_search",
    "compare_train_prices", "search_app",
    "cinema_search", "cinema_schedule",
    "cinema_seats", "afisha_catalog", "afisha_places", "place_schedule",
    "place_info", "concert_schedule", "concert_hall", "nearby_search",
    "weather",
}


def registry(toolset=None):
    env = dict(os.environ)
    env.pop("TBANK_TOOLSET", None)
    if toolset:
        env["TBANK_TOOLSET"] = toolset
    env["TBANK_TRACE"] = "0"
    code = """
import json
from src import server
rows = []
for tool in server.mcp._tool_manager.list_tools():
    ann = tool.annotations
    rows.append({
        "name": tool.name,
        "readOnly": ann.readOnlyHint,
        "destructive": ann.destructiveHint,
    })
print("TRAVEL_REGISTRY=" + json.dumps(rows, sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=90)
    assert proc.returncode == 0, proc.stderr
    line = next(
        item for item in proc.stdout.splitlines()
        if item.startswith("TRAVEL_REGISTRY="))
    return json.loads(line.split("=", 1)[1])


def test_exact_travel_allowlist_and_annotations():
    rows = registry("travel")
    assert {row["name"] for row in rows} == EXPECTED
    assert all(row["readOnly"] is True for row in rows)
    assert all(row["destructive"] is False for row in rows)


def test_full_entrypoint_is_unchanged_and_still_strictly_larger():
    names = {row["name"] for row in registry()}
    assert EXPECTED <= names
    assert {"login", "transfer", "pay_bill", "train_calendar", "get_data"} <= names
    assert len(names) > len(EXPECTED)


if __name__ == "__main__":
    test_exact_travel_allowlist_and_annotations()
    test_full_entrypoint_is_unchanged_and_still_strictly_larger()
    print(f"travel toolset: exact {len(EXPECTED)}-tool read-only registry; full registry preserved")
