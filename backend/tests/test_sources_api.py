from datetime import datetime, timezone

from app.core.exceptions import WeatherError
from app.infrastructure import noaa_metar_client, open_meteo_client
from tests.conftest import make_app

MODELS_PAYLOAD = {
    "localidad": "Viedma",
    "modelos": [
        {"id": "ecmwf_ifs025", "nombre": "ECMWF"},
        {"id": "gfs_global", "nombre": "GFS (NOAA)"},
    ],
    "dias": [
        {
            "fecha": "2026-11-20",
            "modelos": [
                {"modelo": "ecmwf_ifs025", "max": 18.0, "min": 9.0},
                {"modelo": "gfs_global", "max": 17.5, "min": 8.5},
            ],
        }
    ],
}


def observation_payload():
    return {
        "localidad": "Viedma",
        "estacion": "SAVV",
        "hora_utc": datetime.now(timezone.utc).isoformat(),
        "hora": "2026-11-20T14:00",
        "temp": 11.0,
        "humedad": 80.0,
        "viento_kmh": 15.0,
        "viento_dir": 350,
        "presion_hpa": 1017.0,
    }


def test_models_returns_contract(client, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client, "fetch_models", lambda location: dict(MODELS_PAYLOAD)
    )
    res = client.get("/api/v1/models/viedma")
    assert res.status_code == 200
    body = res.get_json()
    assert body["localidad"] == "Viedma"
    assert body["stale"] is False
    assert [m["id"] for m in body["modelos"]] == ["ecmwf_ifs025", "gfs_global"]
    assert body["dias"][0]["modelos"][0]["max"] == 18.0


def test_models_second_call_uses_cache(client, monkeypatch):
    calls = []

    def fake_fetch(location):
        calls.append(1)
        return dict(MODELS_PAYLOAD)

    monkeypatch.setattr(open_meteo_client, "fetch_models", fake_fetch)
    client.get("/api/v1/models/viedma")
    client.get("/api/v1/models/viedma")
    assert len(calls) == 1


def test_models_unknown_location_is_404(client, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client, "fetch_models", lambda location: dict(MODELS_PAYLOAD)
    )
    assert client.get("/api/v1/models/no-existe").status_code == 404


def test_models_provider_failure_is_502(client, monkeypatch):
    def boom(location):
        raise WeatherError("caído")

    monkeypatch.setattr(open_meteo_client, "fetch_models", boom)
    res = client.get("/api/v1/models/viedma")
    assert res.status_code == 502
    assert res.get_json()["error"] == "No se pudo obtener la comparación de modelos por ahora"


def test_models_invalid_payload_is_502(client, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client,
        "fetch_models",
        lambda location: {
            "localidad": "Viedma",
            "modelos": [{"id": "ecmwf_ifs025"}],
            "dias": [],
        },
    )
    assert client.get("/api/v1/models/viedma").status_code == 502


def test_observation_returns_contract(client, monkeypatch):
    monkeypatch.setattr(
        noaa_metar_client, "fetch_observation", lambda location: observation_payload()
    )
    res = client.get("/api/v1/observation/viedma")
    assert res.status_code == 200
    body = res.get_json()
    assert body["estacion"] == "SAVV"
    assert body["temp"] == 11.0
    assert body["vigente"] is True
    assert body["antiguedad_min"] < 5
    assert body["stale"] is False


def test_observation_location_without_station_is_404(client, monkeypatch):
    monkeypatch.setattr(
        noaa_metar_client, "fetch_observation", lambda location: observation_payload()
    )
    # El Cóndor es una playa: no tiene estación METAR
    assert client.get("/api/v1/observation/el-condor").status_code == 404


def test_observation_provider_failure_is_502(client, monkeypatch):
    def boom(location):
        raise WeatherError("caído")

    monkeypatch.setattr(noaa_metar_client, "fetch_observation", boom)
    res = client.get("/api/v1/observation/viedma")
    assert res.status_code == 502
    assert res.get_json()["error"] == "No se pudo obtener la observación por ahora"


def test_observation_falls_back_to_stale(monkeypatch):
    # TTL 0: el dato guardado nunca es fresco, así que siempre intenta refrescar
    client = make_app(CACHE_TTL_OBSERVATION=0).test_client()

    monkeypatch.setattr(
        noaa_metar_client, "fetch_observation", lambda location: observation_payload()
    )
    client.get("/api/v1/observation/viedma")

    def boom(location):
        raise WeatherError("caído")

    monkeypatch.setattr(noaa_metar_client, "fetch_observation", boom)
    res = client.get("/api/v1/observation/viedma")
    assert res.status_code == 200
    assert res.get_json()["stale"] is True
