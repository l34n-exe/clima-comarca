from datetime import datetime, timedelta, timezone
from typing import Any

import pytest  # pyright: ignore[reportMissingImports]

from app.api.schemas.models_schema import serialize_models
from app.api.schemas.observation_schema import serialize_observation
from app.core.exceptions import WeatherError
from app.infrastructure import noaa_metar_client, open_meteo_client

MODELS = ("ecmwf_ifs025", "gfs_global", "icon_global", "gem_global")
LOCATION = {"nombre": "Viedma", "lat": -40.81, "lon": -62.99}

SAMPLE = """Viedma Aerodrome, Argentina (SAVV) 40-51S 063-01W 7M
Oct 27, 2026 - 06:00 AM EDT / 2026.10.27 1000 UTC
Wind: from the N (350 degrees) at 9 MPH (8 KT) (direction variable):0
Temperature: 51 F (11 C)
Relative Humidity: 81%
Pressure (altimeter): 30.03 in. Hg (1017 hPa)
"""


@pytest.fixture
def cfg(app):
    app.config.update(
        WEATHER_MODELS=MODELS,
        WEATHER_API_URL="http://x",
        TIMEZONE="America/Argentina/Buenos_Aires",
    )
    return app


def raw_models(models, bad=None):
    daily: dict[str, Any] = {"time": ["2026-11-18", "2026-11-19"]}
    for i, model in enumerate(models):
        daily[f"temperature_2m_max_{model}"] = [16 + i, 17 + i]
        daily[f"temperature_2m_min_{model}"] = [9 + i, 10 + i]
    if bad:
        daily[f"temperature_2m_max_{bad}"][1] = None
    return {"daily": daily}


def test_parse_decoded_sample(cfg):
    with cfg.app_context():
        data = noaa_metar_client.parse_decoded(SAMPLE)
    assert data["temp"] == 11.0
    assert data["humedad"] == 81.0
    assert data["presion_hpa"] == 1017.0
    assert data["viento_dir"] == 350
    assert data["viento_kmh"] == 15
    assert data["hora_utc"] == "2026-10-27T10:00:00+00:00"
    assert data["hora"] == "2026-10-27T07:00"


def test_parse_calm_and_missing_optionals(cfg):
    text = "x\nOct 27, 2026 - 06:00 AM EDT / 2026.10.27 1000 UTC\nWind: Calm:0\nTemperature: 32 F (0 C)\n"
    with cfg.app_context():
        data = noaa_metar_client.parse_decoded(text)
    assert data["temp"] == 0.0
    assert data["viento_kmh"] == 0
    assert data["viento_dir"] is None
    assert data["humedad"] is None
    assert data["presion_hpa"] is None


def test_parse_without_temperature_fails(cfg):
    with cfg.app_context(), pytest.raises(WeatherError):
        noaa_metar_client.parse_decoded(
            "Oct 27, 2026 - 06:00 AM EDT / 2026.10.27 1000 UTC\n"
        )


def test_fetch_observation_rejects_bad_station(cfg):
    with cfg.app_context(), pytest.raises(WeatherError):
        noaa_metar_client.fetch_observation({"nombre": "X", "estacion": "../etc"})


def test_serialize_observation_age(cfg):
    with cfg.app_context():
        payload = noaa_metar_client.parse_decoded(SAMPLE)
        payload.update(localidad="Viedma", estacion="SAVV", stale=False)
        observed = datetime.fromisoformat(payload["hora_utc"])
        fresh = serialize_observation(payload, now=observed + timedelta(minutes=35))
        old = serialize_observation(payload, now=observed + timedelta(hours=5))
    assert fresh["antiguedad_min"] == 35
    assert fresh["vigente"] is True
    assert old["antiguedad_min"] == 300
    assert old["vigente"] is False


def test_fetch_models_all(cfg, monkeypatch):
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw_models(MODELS))
    with cfg.app_context():
        data = open_meteo_client.fetch_models(LOCATION)
    assert [model["id"] for model in data["modelos"]] == list(MODELS)
    assert len(data["dias"]) == 2
    assert len(data["dias"][0]["modelos"]) == 4


def test_fetch_models_drops_incomplete_model(cfg, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client,
        "_request",
        lambda url, params: raw_models(MODELS, bad="gem_global"),
    )
    with cfg.app_context():
        data = open_meteo_client.fetch_models(LOCATION)
    assert "gem_global" not in [model["id"] for model in data["modelos"]]


def test_fetch_models_needs_two(cfg, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client,
        "_request",
        lambda url, params: raw_models(MODELS[:1]),
    )
    with cfg.app_context(), pytest.raises(WeatherError):
        open_meteo_client.fetch_models(LOCATION)


def test_serialize_models_roundtrip(cfg, monkeypatch):
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw_models(MODELS))
    with cfg.app_context():
        data = open_meteo_client.fetch_models(LOCATION)
    assert serialize_models({**data, "stale": False}) == {**data, "stale": False}
    data["dias"][0]["modelos"][0]["modelo"] = "inventado"
    with pytest.raises(WeatherError):
        serialize_models({**data, "stale": False})
