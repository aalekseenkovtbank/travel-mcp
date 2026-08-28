"""Trip page contract, rendering, CLI and provider adapter."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.trip_page import (TripPageDocumentV1, render_trip_page_files,
                           trip_page_json_schema)
from src.yandex_venues import YandexVenueProvider
from tests.trip_page_fixtures import trip_document


def test_contract_cross_references_and_required_sections():
    document = TripPageDocumentV1.model_validate(trip_document())
    assert document.schema_version == "trip-page/v1"
    broken = trip_document()
    broken["venues"] = broken["venues"][:2]
    try:
        TripPageDocumentV1.model_validate(broken)
        assert False, "fewer than four venues were accepted"
    except Exception as exc:
        assert "at least 4" in str(exc) or "at least" in str(exc)
    bad_plan = trip_document()
    bad_plan["plans"][0]["days"][0]["stops"][0]["refId"] = "missing"
    try:
        TripPageDocumentV1.model_validate(bad_plan)
        assert False, "unknown plan reference was accepted"
    except Exception as exc:
        assert "unknown plan stop" in str(exc)


def test_renderer_writes_atomic_owner_only_pair_and_escapes_html():
    document = TripPageDocumentV1.model_validate(trip_document())
    with tempfile.TemporaryDirectory(prefix="trip-page-") as directory:
        previous = os.environ.get("YANDEX_VENUE_STORAGE_ALLOWED")
        os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = "1"
        os.environ["YANDEX_MAPS_API_KEY"] = "must-never-appear"
        try:
            result = render_trip_page_files(document, output_dir=directory, basename="weekend")
            html = Path(result.html_path).read_text(encoding="utf-8")
            sidecar = Path(result.json_path).read_text(encoding="utf-8")
            assert "Выходные &lt;в Казани&gt;" in html
            assert "must-never-appear" not in html + sidecar
            assert "tile.openstreetmap.org" in html and "window.L" in html
            assert "Рестораны и бары" in html and "Три сценария поездки" in html
            assert stat.S_IMODE(Path(result.html_path).stat().st_mode) == 0o600
            assert stat.S_IMODE(Path(result.json_path).stat().st_mode) == 0o600
            try:
                render_trip_page_files(document, output_dir=directory, basename="weekend")
                assert False, "existing files were overwritten implicitly"
            except FileExistsError:
                pass
        finally:
            if previous is None:
                os.environ.pop("YANDEX_VENUE_STORAGE_ALLOWED", None)
            else:
                os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = previous
            os.environ.pop("YANDEX_MAPS_API_KEY", None)


def test_schema_and_cli_work_without_web_project():
    schema = trip_page_json_schema()
    assert "schemaVersion" in schema["properties"]
    with tempfile.TemporaryDirectory(prefix="trip-cli-") as directory:
        root = Path(directory)
        source = root / "trip.json"
        output = root / "result.html"
        source.write_text(json.dumps(trip_document(), ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, YANDEX_VENUE_STORAGE_ALLOWED="1")
        proc = subprocess.run(
            [sys.executable, "-m", "src.trip_cli", "render-trip", str(source),
             "-o", str(output)], cwd=ROOT, env=env, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert output.exists() and output.with_suffix(".json").exists()
        schema_proc = subprocess.run(
            [sys.executable, "-m", "src.trip_cli", "trip-page-schema"],
            cwd=ROOT, env=env, capture_output=True, text=True)
        assert schema_proc.returncode == 0
        assert json.loads(schema_proc.stdout)["properties"]["schemaVersion"]


def test_fastmcp_renderer_accepts_nested_contract_and_returns_structured_paths():
    from src import server
    with tempfile.TemporaryDirectory(prefix="trip-mcp-") as directory:
        previous = os.environ.get("YANDEX_VENUE_STORAGE_ALLOWED")
        os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = "1"
        try:
            content, structured = asyncio.run(server.mcp._tool_manager.call_tool(
                "render_trip_page", {
                    "document": trip_document(), "output_dir": directory,
                    "basename": "mcp-result",
                }, convert_result=True))
        finally:
            if previous is None:
                os.environ.pop("YANDEX_VENUE_STORAGE_ALLOWED", None)
            else:
                os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = previous
        assert Path(structured["htmlPath"]).exists()
        assert Path(structured["jsonPath"]).exists()
        fallback = "\n".join(item.text for item in content if item.type == "text")
        assert json.loads(fallback)["htmlPath"] == structured["htmlPath"]


def test_yandex_contract_adapter_requires_every_display_field():
    payload = json.loads((ROOT / "tests/fixtures/yandex_venues_contract.json").read_text())

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    import src.yandex_venues as module
    saved = module.requests.get
    previous = os.environ.get("YANDEX_VENUE_STORAGE_ALLOWED")
    os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = "1"
    module.requests.get = lambda *args, **kwargs: Response()
    try:
        result = YandexVenueProvider(api_key="secret").search("Казань", "рестораны")
    finally:
        module.requests.get = saved
        if previous is None:
            os.environ.pop("YANDEX_VENUE_STORAGE_ALLOWED", None)
        else:
            os.environ["YANDEX_VENUE_STORAGE_ALLOWED"] = previous
    assert len(result.venues) == 1 and result.rejected_count == 1
    venue = result.venues[0]
    assert venue.rating == 4.8 and venue.review_count == 321 and venue.photos
    assert "secret" not in json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


if __name__ == "__main__":
    test_contract_cross_references_and_required_sections()
    test_renderer_writes_atomic_owner_only_pair_and_escapes_html()
    test_schema_and_cli_work_without_web_project()
    test_fastmcp_renderer_accepts_nested_contract_and_returns_structured_paths()
    test_yandex_contract_adapter_requires_every_display_field()
    print("trip page: contract, renderer, CLI and Yandex adapter OK")
