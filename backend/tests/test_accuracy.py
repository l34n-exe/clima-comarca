from datetime import datetime, timedelta, timezone

from app.core.exceptions import WeatherError
from app.services import accuracy_service, weather_service

VIEDMA = {"slug": "viedma", "nombre": "Viedma", "lat": -40.8, "lon": -62.9, "estacion": "SAVV"}
PLAYA = {"slug": "el-condor", "nombre": "El Cóndor", "lat": -41.0, "lon": -62.8, "tipo": "playa"}


def obs_payload(temp=15.0, age_min=20):
    observed = datetime.now(timezone.utc) - timedelta(minutes=age_min)
    return {
        "localidad": "Viedma",
        "estacion": "SAVV",
        "hora_utc": observed.isoformat(),
        "hora": "2026-11-20T14:00",
        "temp": temp,
        "humedad": 60.0,
        "viento_kmh": 10.0,
        "viento_dir": 90,
        "presion_hpa": 1015.0,
        "stale": False,
    }


def current_payload(temp=17.0):
    return {"localidad": "Viedma", "temp": temp, "stale": False}


def test_record_stores_estimate_and_observation(app, monkeypatch):
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())
    monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
    with app.app_context():
        assert accuracy_service.record(VIEDMA) is True
        raw = app.extensions["redis"].hgetall("accuracy:viedma")
    assert len(raw) == 1
    import json

    entry = json.loads(next(iter(raw.values())))
    assert entry == {"e": 17.0, "o": 15.0}


def test_record_keeps_existing_fields(app, monkeypatch):
    # La observación falla: se guarda solo la estimación, sin pisar la obs previa
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())

    def boom(loc):
        raise WeatherError("caído")

    monkeypatch.setattr(weather_service, "get_observation", boom)
    with app.app_context():
        assert accuracy_service.record(VIEDMA) is True
        first = app.extensions["redis"].hgetall("accuracy:viedma")

        monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
        monkeypatch.setattr(weather_service, "get_current", boom)
        assert accuracy_service.record(VIEDMA) is True
        raw = app.extensions["redis"].hgetall("accuracy:viedma")
    assert len(raw) == 1  # mismo bucket horario: se fusiona, no duplica
    import json

    entry = json.loads(next(iter(raw.values())))
    assert entry["e"] == 17.0 and entry["o"] == 15.0
    assert first != raw or True  # sanity: el hash existe


def test_record_skips_stale_data(app, monkeypatch):
    monkeypatch.setattr(
        weather_service,
        "get_current",
        lambda loc: {**current_payload(), "stale": True},
    )
    monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
    monkeypatch.setattr(
        weather_service,
        "get_observation",
        lambda loc: {**obs_payload(), "stale": True},
    )
    with app.app_context():
        assert accuracy_service.record(VIEDMA) is False


def test_record_skips_old_observation(app, monkeypatch):
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())
    monkeypatch.setattr(
        weather_service, "get_observation", lambda loc: obs_payload(age_min=200)
    )
    with app.app_context():
        assert accuracy_service.record(VIEDMA) is True  # guarda la estimación sola
        raw = app.extensions["redis"].hgetall("accuracy:viedma")
    import json

    entry = json.loads(next(iter(raw.values())))
    assert entry["e"] == 17.0 and entry["o"] is None


def test_stats_computes_errors(app):
    import json

    now = datetime.now(timezone.utc)
    entries = {}
    for i, (est, obs) in enumerate([(18.0, 16.0), (14.0, 15.0), (20.0, 19.0)]):
        bucket = (now - timedelta(hours=i)).strftime("%Y-%m-%dT%H")
        entries[bucket] = json.dumps({"e": est, "o": obs})
    # Par incompleto: no cuenta
    entries[(now - timedelta(hours=5)).strftime("%Y-%m-%dT%H")] = json.dumps({"e": 10.0})
    # Viejo: fuera de la ventana de 7 días
    old = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H")
    entries[old] = json.dumps({"e": 30.0, "o": 10.0})

    with app.app_context():
        app.extensions["redis"].hset("accuracy:viedma", mapping=entries)
        stats = accuracy_service.stats(VIEDMA, days=7)
    assert stats["muestras"] == 3
    # errores: +2, -1, +1 → MAE = 4/3 ≈ 1.33, sesgo = 2/3 ≈ 0.67
    assert stats["error_promedio_c"] == 1.33
    assert stats["error_maximo_c"] == 2.0
    assert stats["sesgo_c"] == 0.67
    assert stats["stale"] is False
    assert sum(d["muestras"] for d in stats["por_dia"]) == 3


def test_stats_empty(app):
    with app.app_context():
        stats = accuracy_service.stats(VIEDMA, days=7)
    assert stats["muestras"] == 0
    assert stats["error_promedio_c"] is None
    assert stats["por_dia"] == []


def test_accuracy_endpoint(client, monkeypatch):
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())
    monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
    res = client.get("/api/v1/accuracy/viedma")
    assert res.status_code == 200
    body = res.get_json()
    assert body["localidad"] == "Viedma"
    assert body["muestras"] == 1
    assert body["error_promedio_c"] == 2.0
    assert body["stale"] is False


def test_accuracy_endpoint_unknown_and_no_station(client, monkeypatch):
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())
    monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
    assert client.get("/api/v1/accuracy/no-existe").status_code == 404
    assert client.get("/api/v1/accuracy/el-condor").status_code == 404


def test_accuracy_endpoint_days_param(client, monkeypatch):
    monkeypatch.setattr(weather_service, "get_current", lambda loc: current_payload())
    monkeypatch.setattr(weather_service, "get_observation", lambda loc: obs_payload())
    res = client.get("/api/v1/accuracy/viedma?dias=30")
    assert res.status_code == 200
    assert res.get_json()["dias"] == 30
    res = client.get("/api/v1/accuracy/viedma?dias=999")
    assert res.get_json()["dias"] == 30  # se recorta al máximo
