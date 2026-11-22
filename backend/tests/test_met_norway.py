from datetime import datetime, timedelta, timezone

import pytest  # pyright: ignore[reportMissingImports]

from app.core.exceptions import WeatherError
from app.api.schemas.weather_schema import serialize_forecast
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
    # MET Norway no informa ráfagas: deben ser null, nunca un relleno
    assert all(h["rafaga_kmh"] is None for h in data["horas"])
    assert day["rafaga_max_kmh"] is None
    # Sol en ISO completo y no vacío (el frontend hace slice(11,16))
    assert day["amanecer"] and day["atardecer"]
    assert len(day["amanecer"]) >= 16 and day["amanecer"][10] == "T"
    assert day["prob_lluvia"] in (0.0, 100.0)


def test_forecast_gusts_never_below_wind(app, monkeypatch):
    """Si algún día hay ráfagas, no pueden ser menores que el viento medio."""
    timeseries = [entry(i) for i in range(48)]
    monkeypatch.setattr(
        met_norway_client.http,
        "get",
        lambda *a, **k: FakeResp({"properties": {"timeseries": timeseries}}),
    )
    with app.app_context():
        data = met_norway_client.fetch_forecast(VIEDMA)
    for h in data["horas"]:
        if h["rafaga_kmh"] is not None:
            assert h["rafaga_kmh"] >= h["viento_kmh"]


def _forecast_day(**overrides):
    day = {
        "fecha": "2026-11-22",
        "max": 20.0,
        "min": 10.0,
        "lluvia_mm": 0.0,
        "prob_lluvia": 0.0,
        "viento_max_kmh": 15.0,
        "rafaga_max_kmh": None,
        "amanecer": "2026-11-22T05:39",
        "atardecer": "2026-11-22T20:16",
        "codigo": 0,
        "descripcion": "Despejado",
    }
    day.update(overrides)
    return day


def _hour():
    return {
        "hora": "2026-11-22T15:00",
        "temp": 20.0,
        "viento_kmh": 10.0,
        "rafaga_kmh": None,
        "prob_lluvia": 0.0,
    }


def test_schema_accepts_null_gusts(app):
    with app.app_context():
        payload = serialize_forecast(
            {
                "localidad": "Viedma",
                "dias": [_forecast_day()],
                "horas": [_hour()] * 24,
                "stale": False,
                "fuente": "met-norway",
            }
        )
    assert payload["dias"][0]["rafaga_max_kmh"] is None
    assert payload["horas"][0]["rafaga_kmh"] is None
    assert payload["fuente"] == "met-norway"


def test_schema_rejects_empty_sun(app):
    with app.app_context(), pytest.raises(WeatherError):
        serialize_forecast(
            {
                "localidad": "Viedma",
                "dias": [_forecast_day(amanecer="")],
                "horas": [_hour()] * 24,
                "stale": False,
            }
        )


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
        assert fetch(VIEDMA)["fuente"] == "met-norway"


def test_fallback_tags_primary_source(app, monkeypatch):
    monkeypatch.setattr(
        weather_service.open_meteo_client,
        "fetch_current",
        lambda loc: {"localidad": "Viedma", "temp": 20.0},
    )
    with app.app_context():
        fetch = weather_service._with_fallback(
            weather_service.open_meteo_client.fetch_current,
            weather_service.met_norway_client.fetch_current,
        )
        assert fetch(VIEDMA)["fuente"] == "open-meteo"


def test_met_norway_rounds_coordinates_and_sends_user_agent(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None):
        calls.append((url, params, headers))
        return FakeResp(payload())

    monkeypatch.setattr(met_norway_client.http, "get", fake_get)
    location = {**VIEDMA, "lat": -40.8135123, "lon": -62.9967456}
    with app.app_context():
        met_norway_client.fetch_current(location)

    _, params, headers = calls[0]
    assert params["lat"] == -40.8135
    assert params["lon"] == -62.9967
    assert headers["User-Agent"] == met_norway_client.USER_AGENT


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
