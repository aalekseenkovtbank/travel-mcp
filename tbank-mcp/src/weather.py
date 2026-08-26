"""Open-Meteo forecast and ERA5 climate estimates for the travel MCP."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

import requests

from .client import TbankApiError

FORECAST_DAYS = 16
CLIMATE_START = "1991-01-01"
CLIMATE_END = "2020-12-31"
PRECIPITATION_DAY_MM = 1.0
FORECAST_URL = os.environ.get(
    "OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
ARCHIVE_URL = os.environ.get(
    "OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive")
TIMEOUT_SECONDS = max(1.0, float(os.environ.get("TRAVEL_PROVIDER_TIMEOUT_SECONDS", "15")))


def _iso(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value or ""))
    except ValueError as exc:
        raise TbankApiError("BAD_DATE", f"{field} должен быть YYYY-MM-DD.") from exc


def _coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise TbankApiError("BAD_COORDINATES", "Координаты должны быть числами.") from exc
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise TbankApiError(
            "BAD_COORDINATES", "latitude должен быть -90..90, longitude -180..180.")
    return lat, lon


def _request(requester: Any, url: str, params: dict[str, Any], source: str) -> dict[str, Any]:
    try:
        response = requester.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", f"{source} не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError("SOURCE_UNAVAILABLE", f"{source} недоступен: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise TbankApiError("BAD_SOURCE_RESPONSE", f"{source} вернул невалидный JSON.") from exc
    if not isinstance(payload, dict):
        raise TbankApiError("BAD_SOURCE_RESPONSE", f"{source} вернул не объект.")
    if payload.get("error"):
        raise TbankApiError(
            "SOURCE_ERROR", f"{source}: {payload.get('reason') or 'неизвестная ошибка'}")
    return payload


def _number(values: Any, index: int) -> float | None:
    if not isinstance(values, list) or index >= len(values):
        return None
    value = values[index]
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _forecast(latitude: float, longitude: float, requester: Any) -> dict[str, dict[str, Any]]:
    payload = _request(requester, FORECAST_URL, {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": FORECAST_DAYS,
        "timezone": "Europe/Moscow",
    }, "Open-Meteo Forecast")
    daily = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}
    dates = daily.get("time") if isinstance(daily.get("time"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for index, raw_date in enumerate(dates):
        minimum = _number(daily.get("temperature_2m_min"), index)
        maximum = _number(daily.get("temperature_2m_max"), index)
        precipitation = _number(daily.get("precipitation_probability_max"), index)
        code = _number(daily.get("weather_code"), index)
        if None in (minimum, maximum, precipitation, code):
            continue
        day = str(raw_date)
        out[day] = {
            "date": day,
            "kind": "forecast",
            "temperatureMinC": round(minimum),
            "temperatureMaxC": round(maximum),
            "precipitationProbabilityPct": max(0, min(100, round(precipitation))),
            "weatherCode": max(0, round(code)),
        }
    if not out:
        raise TbankApiError("EMPTY_SOURCE", "Open-Meteo не вернул дневной прогноз.")
    return out


def _history(latitude: float, longitude: float, requester: Any) -> list[dict[str, Any]]:
    payload = _request(requester, ARCHIVE_URL, {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": CLIMATE_START,
        "end_date": CLIMATE_END,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "models": "era5",
        "timezone": "Europe/Moscow",
    }, "Open-Meteo ERA5")
    daily = payload.get("daily") if isinstance(payload.get("daily"), dict) else {}
    dates = daily.get("time") if isinstance(daily.get("time"), list) else []
    out: list[dict[str, Any]] = []
    for index, raw_date in enumerate(dates):
        minimum = _number(daily.get("temperature_2m_min"), index)
        maximum = _number(daily.get("temperature_2m_max"), index)
        precipitation = _number(daily.get("precipitation_sum"), index)
        if None in (minimum, maximum, precipitation):
            continue
        out.append({
            "date": str(raw_date),
            "temperatureMinC": minimum,
            "temperatureMaxC": maximum,
            "precipitationMm": precipitation,
        })
    if not out:
        raise TbankApiError("EMPTY_SOURCE", "Open-Meteo ERA5 не вернул исторические данные.")
    return out


def _month_days(target: date) -> set[str]:
    anchor = target.replace(year=2000)
    return {(anchor + timedelta(days=offset)).isoformat()[5:] for offset in range(-3, 4)}


def _climate_day(target: date, history: list[dict[str, Any]]) -> dict[str, Any] | None:
    wanted = _month_days(target)
    samples = [item for item in history if str(item["date"])[5:] in wanted]
    if not samples:
        return None
    return {
        "date": target.isoformat(),
        "kind": "climate",
        "temperatureMinC": round(mean(item["temperatureMinC"] for item in samples)),
        "temperatureMaxC": round(mean(item["temperatureMaxC"] for item in samples)),
        "precipitationFrequencyPct": round(
            sum(item["precipitationMm"] >= PRECIPITATION_DAY_MM for item in samples) /
            len(samples) * 100),
        "sampleSize": len(samples),
    }


def weather_report(
    *,
    city: str,
    latitude: float,
    longitude: float,
    date_from: str,
    date_to: str,
    requester: Any = requests,
    today: date | None = None,
) -> dict[str, Any]:
    city = str(city or "").strip()
    if not city:
        raise TbankApiError("BAD_CITY", "Передай city.")
    lat, lon = _coordinates(latitude, longitude)
    start, end = _iso(date_from, "date_from"), _iso(date_to, "date_to")
    if end < start:
        raise TbankApiError("BAD_DATES", "date_to должен быть не раньше date_from.")
    count = (end - start).days + 1
    if count > 30:
        raise TbankApiError("BAD_DATES", "Диапазон погоды не должен превышать 30 дней.")
    dates = [start + timedelta(days=offset) for offset in range(count)]
    current = today or datetime.now(ZoneInfo("Europe/Moscow")).date()
    forecast_end = current + timedelta(days=FORECAST_DAYS - 1)
    needs_forecast = any(current <= item <= forecast_end for item in dates)
    needs_history = any(not current <= item <= forecast_end for item in dates)
    warnings: list[str] = []
    forecast: dict[str, dict[str, Any]] = {}
    history: list[dict[str, Any]] = []

    if needs_forecast:
        try:
            forecast = _forecast(lat, lon, requester)
        except TbankApiError as exc:
            warnings.append(str(exc.message))
            needs_history = True  # climate is the honest fallback for missing forecast.
    if needs_history:
        try:
            history = _history(lat, lon, requester)
        except TbankApiError as exc:
            warnings.append(str(exc.message))

    days: list[dict[str, Any]] = []
    for item in dates:
        forecast_day = forecast.get(item.isoformat())
        if forecast_day:
            days.append(forecast_day)
            continue
        climate_day = _climate_day(item, history) if history else None
        if climate_day:
            days.append(climate_day)
    if len(days) < len(dates):
        warnings.append(f"Погода доступна для {len(days)} из {len(dates)} дней.")
    kinds = {item["kind"] for item in days}
    source = ("Open-Meteo Forecast + ERA5" if len(kinds) > 1 else
              "Open-Meteo Forecast" if "forecast" in kinds else
              "Open-Meteo ERA5" if "climate" in kinds else "Open-Meteo")
    return {
        "data": {
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "dateFrom": start.isoformat(),
            "dateTo": end.isoformat(),
            "days": days,
        },
        "warnings": list(dict.fromkeys(warnings)),
        "source": source,
        "complete": len(days) == len(dates),
    }
