from datetime import datetime, timedelta, timezone

import pytest  # pyright: ignore[reportMissingImports]

from app.core.exceptions import WeatherError
from app.infrastructure import met_norway_client
from app.services import weather_service

VIEDMA = {"slug": "viedma", "nombre": "Viedma", "lat": -40.8, "lon": -62.9, "estacion": "SAVV"}


def entry(hours_ahead, temp=15.0, symbol="partlycloudy_day", precip=0.0, wind=5.0):
    t = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    return {
        "time": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data": {
            "instant": {
                "details": {
                    "air_temperature": temp,
                    "wind_speed": wind,
                    "wind_from_direction": 180,
                    "relative_humidity": 70,
                }
            },
            "next_1_hours": {
                "summary": {"symbol_code": symbol},
                "details": {"precipitation_amount": precip},
            },
        },
    }


def payload(n=48):
    return {"properties": {"timeseries": [entry(i) for i in range(n)]}}


def test_fetch_current(app, monkeypatch):
    monkeypatch.setattr(
        met_norway_client.http, "get", lambda *a, **k: FakeResp(payload())
    )
    with app.app_context():
        data = met_norway_client.fetch_current(VIEDMA)
    assert data["localidad"] == "Viedma"
    assert data["temp"] == 15.0
    assert data["viento_kmh"] == 18.0  # m/s → km/h
    assert data["codigo"] == 2
    assert data["descripcion"] == "Parcialmente nublado"
    assert data["hora"]


def test_fetch_forecast(app, monkeypatch):
    timeseries = [entry(i, temp=10 + i % 8, precip=0.5 if i % 12 == 0 else 0) for i in range(48)]
    monkeypatch.setattr(
        met_norway_client.http,
        "get",
        lambda *a, **k: FakeResp({"properties": {"timeseries": timeseries}}),
    )
    with app.app_context():
        data = met_norway_client.fetch_forecast(VIEDMA)
    assert data["localidad"] == "Viedma"
    assert len(data["horas"]) == 24
    assert len(data["dias"]) >= 1
    day = data["dias"][0]
    assert day["max"] >= day["min"]
    assert day["amanecer"] and day["atardecer"]
    assert day["prob_lluvia"] in (0.0, 100.0)


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_fallback_uses_secondary_when_primary_fails(app, monkeypatch):
    def boom(location):
        raise WeatherError("429")

    monkeypatch.setattr(weather_service.open_meteo_client, "fetch_current", boom)
    monkeypatch.setattr(
        weather_service.met_norway_client,
        "fetch_current",
        lambda loc: {"localidad": "Viedma", "temp": 15.0, "stale": False},
    )
    # Forzamos el fetch directo (sin caché)
    with app.app_context():
        fetch = weather_service._with_fallback(
            weather_service.open_meteo_client.fetch_current,
            weather_service.met_norway_client.fetch_current,
        )
        assert fetch(VIEDMA)["temp"] == 15.0


def test_fallback_raises_when_both_fail(app, monkeypatch):
    def boom(location):
        raise WeatherError("caído")

    monkeypatch.setattr(weather_service.open_meteo_client, "fetch_current", boom)
    monkeypatch.setattr(weather_service.met_norway_client, "fetch_current", boom)
    with app.app_context(), pytest.raises(WeatherError):
        weather_service._with_fallback(
            weather_service.open_meteo_client.fetch_current,
            weather_service.met_norway_client.fetch_current,
        )(VIEDMA)
