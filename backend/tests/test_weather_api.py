from app.infrastructure import open_meteo_client
from tests.conftest import make_app

FAKE = {
    "localidad": "Viedma",
    "temp": 18.0,
    "sensacion": 17.0,
    "humedad": 60,
    "viento_kmh": 12.0,
    "viento_dir": 90,
    "codigo": 1,
    "descripcion": "Mayormente despejado",
    "hora": "2026-11-18T12:00",
}


def test_unknown_location_is_404(client):
    assert client.get("/api/v1/weather/no-existe").status_code == 404


def test_second_call_uses_cache(client, monkeypatch):
    calls = []

    def fake_fetch(location):
        calls.append(1)
        return dict(FAKE)

    monkeypatch.setattr(open_meteo_client, "fetch_current", fake_fetch)
    client.get("/api/v1/weather/viedma")
    res = client.get("/api/v1/weather/viedma")

    assert len(calls) == 1
    assert res.get_json()["stale"] is False


def test_stale_when_provider_fails(monkeypatch):
    # TTL 0: el dato guardado nunca es fresco, así que siempre intenta refrescar
    client = make_app(CACHE_TTL_CURRENT=0).test_client()

    monkeypatch.setattr(open_meteo_client, "fetch_current", lambda loc: dict(FAKE))
    client.get("/api/v1/weather/viedma")

    def boom(location):
        raise open_meteo_client.WeatherError("caído")

    monkeypatch.setattr(open_meteo_client, "fetch_current", boom)
    res = client.get("/api/v1/weather/viedma")

    assert res.status_code == 200
    assert res.get_json()["stale"] is True


def test_502_when_provider_fails_and_no_cache(client, monkeypatch):
    def boom(location):
        raise open_meteo_client.WeatherError("caído")

    monkeypatch.setattr(open_meteo_client, "fetch_current", boom)
    assert client.get("/api/v1/weather/viedma").status_code == 502


def test_invalid_normalized_weather_is_502(client, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client,
        "fetch_current",
        lambda location: {"localidad": location["nombre"], "temp": 18},
    )
    response = client.get("/api/v1/weather/viedma")
    assert response.status_code == 502
    assert response.get_json()["error"] == "No se pudo obtener el clima por ahora"


def test_forecast_contract_is_returned(client, monkeypatch):
    day = {
        "fecha": "2026-11-18",
        "max": 22.0,
        "min": 11.0,
        "lluvia_mm": 0.0,
        "prob_lluvia": 20,
        "viento_max_kmh": 18.0,
        "rafaga_max_kmh": 32.0,
        "amanecer": "2026-11-18T06:00",
        "atardecer": "2026-11-18T20:00",
        "codigo": 1,
        "descripcion": "Mayormente despejado",
    }
    hours = [
        {
            "hora": f"2026-11-18T{index:02d}:00",
            "temp": 20.0,
            "viento_kmh": 10.0,
            "rafaga_kmh": 15.0,
            "prob_lluvia": 5,
        }
        for index in range(24)
    ]
    monkeypatch.setattr(
        open_meteo_client,
        "fetch_forecast",
        lambda location: {"localidad": location["nombre"], "dias": [day], "horas": hours},
    )
    response = client.get("/api/v1/forecast/viedma")
    assert response.status_code == 200
    assert response.get_json()["dias"] == [day]
    assert len(response.get_json()["horas"]) == 24
    assert response.get_json()["stale"] is False


def test_invalid_forecast_contract_is_502(client, monkeypatch):
    monkeypatch.setattr(
        open_meteo_client,
        "fetch_forecast",
        lambda location: {
            "localidad": location["nombre"],
            "dias": [{"fecha": "2026-11-18"}],
            "horas": [],
        },
    )
    response = client.get("/api/v1/forecast/viedma")
    assert response.status_code == 502
