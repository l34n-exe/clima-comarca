import math

from app.infrastructure import open_meteo_client
from app.utils.tides import find_extremes

PERIOD = 12.42  # horas, ciclo de marea semidiurna


def synthetic(hours=72):
    times = [f"2026-11-{16 + h // 24}T{h % 24:02d}:00" for h in range(hours)]
    heights = [2.0 * math.sin(2 * math.pi * h / PERIOD) for h in range(hours)]
    return times, heights


def test_find_extremes_alternate_and_spacing():
    times, heights = synthetic()
    extremes = find_extremes(times, heights)

    kinds = [e["tipo"] for e in extremes]
    assert kinds[0] == "pleamar"
    assert all(a != b for a, b in zip(kinds, kinds[1:]))

    # Entre un extremo y el siguiente pasan ~6.2 horas
    from datetime import datetime
    moments = [datetime.fromisoformat(e["hora"]) for e in extremes]
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(moments, moments[1:])]
    assert all(5.8 < g < 6.6 for g in gaps)


def test_first_high_tide_is_close_to_real_peak():
    times, heights = synthetic()
    first = find_extremes(times, heights)[0]
    # El pico real cae a las 03:06 (PERIOD / 4 horas)
    assert first["hora"].endswith(("03:00", "03:01", "03:02", "03:03", "03:04",
                                   "03:05", "03:06", "03:07", "03:08", "03:09", "03:10"))
    assert abs(first["altura_m"] - 2.0) < 0.05


def test_fetch_tides_normalizes(app, monkeypatch):
    times, heights = synthetic()
    raw = {"hourly": {"time": times, "sea_level_height_msl": heights}}
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw)

    with app.app_context():
        data = open_meteo_client.fetch_tides(
            {"nombre": "El Cóndor", "lat": -41.06, "lon": -62.81}
        )

    assert data["localidad"] == "El Cóndor"
    assert len(data["serie"]) == 72
    assert data["mareas"][0]["tipo"] == "pleamar"


def test_fetch_tides_with_null_values_fails(app, monkeypatch):
    times, heights = synthetic()
    heights_with_null: list[float | None] = list(heights)
    heights_with_null[10] = None
    raw = {"hourly": {"time": times, "sea_level_height_msl": heights_with_null}}
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw)

    with app.app_context():
        try:
            open_meteo_client.fetch_tides({"nombre": "X", "lat": 0, "lon": 0})
            assert False, "debería lanzar WeatherError"
        except open_meteo_client.WeatherError:
            pass


def test_fetch_tides_rejects_mismatched_series(app, monkeypatch):
    raw = {"hourly": {"time": ["2026-11-16T00:00"] * 3, "sea_level_height_msl": [1.0]}}
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw)
    with app.app_context():
        try:
            open_meteo_client.fetch_tides({"nombre": "X", "lat": 0, "lon": 0})
            assert False, "debería lanzar WeatherError"
        except open_meteo_client.WeatherError:
            pass


def test_fetch_forecast_rejects_mismatched_columns(app, monkeypatch):
    raw = {
        "daily": {
            "time": ["2026-11-16", "2026-11-17"],
            "temperature_2m_max": [20.0],
            "temperature_2m_min": [10.0, 11.0],
            "precipitation_sum": [0.0, 0.0],
            "wind_speed_10m_max": [10.0, 12.0],
            "weather_code": [1, 2],
        }
    }
    monkeypatch.setattr(open_meteo_client, "_request", lambda url, params: raw)
    with app.app_context():
        try:
            open_meteo_client.fetch_forecast({"nombre": "X", "lat": 0, "lon": 0})
            assert False, "debería lanzar WeatherError"
        except open_meteo_client.WeatherError:
            pass


def test_tides_endpoint_only_for_beaches(client, monkeypatch):
    monkeypatch.setattr(open_meteo_client, "fetch_tides", lambda loc: {
        "localidad": loc["nombre"],
        "mareas": [],
        "serie": [],
        "referencia": "nivel medio del mar",
        "aviso": "estimación",
    })

    assert client.get("/api/v1/tides/viedma").status_code == 400
    assert client.get("/api/v1/tides/no-existe").status_code == 404

    res = client.get("/api/v1/tides/la-baliza")
    assert res.status_code == 200
    assert res.get_json()["stale"] is False


def test_tides_endpoint_500_when_provider_fails(client, monkeypatch):
    def boom(location):
        raise open_meteo_client.WeatherError("caído")

    monkeypatch.setattr(open_meteo_client, "fetch_tides", boom)
    res = client.get("/api/v1/tides/el-espigon")
    assert res.status_code == 500
    assert "mareas" in res.get_json()["error"]
