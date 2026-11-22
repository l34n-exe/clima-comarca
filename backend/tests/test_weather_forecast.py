from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest  # pyright: ignore[reportMissingImports]

from app.core.exceptions import WeatherError
from app.infrastructure import open_meteo_client


def forecast_payload():
    now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).replace(
        minute=0, second=0, microsecond=0
    )
    times = [
        (now + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:00")
        for offset in range(-1, 48)
    ]
    return {
        "daily": {
            "time": ["2026-11-19"],
            "temperature_2m_max": [24.0],
            "temperature_2m_min": [12.0],
            "precipitation_sum": [1.2],
            "precipitation_probability_max": [35],
            "wind_speed_10m_max": [25.0],
            "wind_gusts_10m_max": [48.0],
            "sunrise": ["2026-11-19T06:10"],
            "sunset": ["2026-11-19T20:15"],
            "weather_code": [2],
        },
        "hourly": {
            "time": times,
            "temperature_2m": [20.0] * len(times),
            "wind_speed_10m": [10.0] * len(times),
            "wind_gusts_10m": [18.0] * len(times),
            "precipitation_probability": [5] * len(times),
        },
    }


def test_fetch_forecast_includes_gusts_sun_times_and_next_24_hours(app, monkeypatch):
    payload = forecast_payload()
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: payload)
    with app.app_context():
        forecast = open_meteo_client.fetch_forecast(
            {"nombre": "Viedma", "lat": -40.8, "lon": -63.0}
        )

    assert forecast["dias"][0]["rafaga_max_kmh"] == 48.0
    assert forecast["dias"][0]["rafaga_max_kmh"] >= forecast["dias"][0]["viento_max_kmh"]
    assert forecast["dias"][0]["prob_lluvia"] == 35
    assert forecast["dias"][0]["amanecer"] == "2026-11-19T06:10"
    assert forecast["dias"][0]["atardecer"] == "2026-11-19T20:15"
    assert len(forecast["horas"]) == 24
    assert forecast["horas"][0]["hora"] == payload["hourly"]["time"][1]
    for hour in forecast["horas"]:
        assert hour["rafaga_kmh"] is None or hour["rafaga_kmh"] >= hour["viento_kmh"]


def test_fetch_forecast_without_gusts_returns_null(app, monkeypatch):
    payload = forecast_payload()
    del payload["hourly"]["wind_gusts_10m"]
    payload["daily"]["wind_gusts_10m_max"] = [None] * len(payload["daily"]["time"])
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: payload)

    with app.app_context():
        forecast = open_meteo_client.fetch_forecast(
            {"nombre": "Viedma", "lat": -40.8, "lon": -63.0}
        )

    assert forecast["dias"][0]["rafaga_max_kmh"] is None
    assert forecast["horas"][0]["rafaga_kmh"] is None
    for hour in forecast["horas"]:
        assert hour["rafaga_kmh"] is None or hour["rafaga_kmh"] >= hour["viento_kmh"]


def test_fetch_forecast_rejects_malformed_gusts(app, monkeypatch):
    payload = forecast_payload()
    payload["hourly"]["wind_gusts_10m"] = ["x"] * len(payload["hourly"]["time"])
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: payload)

    with app.app_context(), pytest.raises(WeatherError, match="wind_gusts_10m"):
        open_meteo_client.fetch_forecast(
            {"nombre": "Viedma", "lat": -40.8, "lon": -63.0}
        )


def test_fetch_current_returns_wind_gusts(app, monkeypatch):
    raw = {
        "current": {
            "temperature_2m": 20.0,
            "apparent_temperature": 19.0,
            "relative_humidity_2m": 55,
            "wind_speed_10m": 18.0,
            "wind_gusts_10m": 31.0,
            "wind_direction_10m": 270,
            "weather_code": 1,
            "time": "2026-11-19T14:00",
        }
    }
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw)

    with app.app_context():
        weather = open_meteo_client.fetch_current(
            {"nombre": "Viedma", "lat": -40.8, "lon": -63.0}
        )

    assert weather["rafaga_kmh"] == 31.0
