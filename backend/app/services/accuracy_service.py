import json
import threading
import time
from datetime import datetime, timezone

from ..infrastructure.redis_client import get_redis
from ..core.exceptions import WeatherError
from . import weather_service

# La observación METAR se reporta ~1 vez por hora; se acepta si tiene
# menos de 90 minutos para que el pareo con la estimación sea honesto
MAX_OBS_AGE_MIN = 90
# 40 días de retención: sobra para "los últimos días" y mantiene Redis chico
RETENTION_SECONDS = 40 * 24 * 3600


def _bucket():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


def _obs_age_min(obs):
    try:
        observed = datetime.fromisoformat(obs["hora_utc"])
    except (KeyError, TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - observed).total_seconds() / 60


def record(location):
    """Guarda la estimación del modelo y la observación METAR de la hora en curso.

    Cada dato se guarda solo si está fresco; si la hora ya tiene registro,
    se completan los campos que falten sin pisar los existentes.
    """
    key = f"accuracy:{location['slug']}"
    bucket = _bucket()
    entry = {"e": None, "o": None}

    try:
        current = weather_service.get_current(location)
        # Solo cuenta la estimación de Open-Meteo: si el respaldo MET Norway
        # respondiera, mezclar dos modelos distintos haría que el "error
        # promedio" no mida a ninguno
        if not current.get("stale") and current.get("fuente") == "open-meteo":
            entry["e"] = current.get("temp")
    except WeatherError:
        pass

    try:
        obs = weather_service.get_observation(location)
        age = _obs_age_min(obs)
        if not obs.get("stale") and age is not None and 0 <= age <= MAX_OBS_AGE_MIN:
            entry["o"] = obs.get("temp")
    except WeatherError:
        pass

    if entry["e"] is None and entry["o"] is None:
        return False

    existing = get_redis().hget(key, bucket)
    if existing:
        try:
            old = json.loads(existing)
            entry["e"] = entry["e"] if entry["e"] is not None else old.get("e")
            entry["o"] = entry["o"] if entry["o"] is not None else old.get("o")
        except (TypeError, ValueError):
            pass

    get_redis().hset(key, bucket, json.dumps(entry))
    get_redis().expire(key, RETENTION_SECONDS)
    return True


def record_in_background(app, location):
    """Llama a los proveedores puede tardar (reintentos, rate limit):
    se hace en un hilo para no bloquear el request ni matar el worker."""

    def target():
        with app.app_context():
            try:
                record(location)
            except Exception:
                app.logger.warning("No se pudo registrar la precisión", exc_info=True)

    threading.Thread(target=target, daemon=True).start()


def stats(location, days):
    """Error del modelo (estimado - observado) sobre los últimos `days` días."""
    raw = get_redis().hgetall(f"accuracy:{location['slug']}") or {}
    cutoff = time.time() - days * 86400
    pairs = []
    daily = {}

    for bucket, value in raw.items():
        try:
            entry = json.loads(value)
            est, obs = entry.get("e"), entry.get("o")
            if est is None or obs is None:
                continue
            ts = datetime.strptime(bucket, "%Y-%m-%dT%H").replace(
                tzinfo=timezone.utc
            ).timestamp()
        except (TypeError, ValueError):
            continue
        if ts < cutoff:
            continue
        error = est - obs
        pairs.append(error)
        daily.setdefault(bucket[:10], []).append(error)

    por_dia = [
        {
            "fecha": fecha,
            "error_c": round(sum(errors) / len(errors), 2),
            "muestras": len(errors),
        }
        for fecha, errors in sorted(daily.items())
    ]

    if not pairs:
        return {
            "localidad": location["nombre"],
            "dias": days,
            "muestras": 0,
            "error_promedio_c": None,
            "error_maximo_c": None,
            "sesgo_c": None,
            "por_dia": [],
            "stale": False,
        }

    return {
        "localidad": location["nombre"],
        "dias": days,
        "muestras": len(pairs),
        "error_promedio_c": round(sum(abs(e) for e in pairs) / len(pairs), 2),
        "error_maximo_c": round(max(abs(e) for e in pairs), 2),
        "sesgo_c": round(sum(pairs) / len(pairs), 2),
        "por_dia": por_dia,
        "stale": False,
    }
