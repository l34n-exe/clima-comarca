from datetime import datetime, timezone

from flask import current_app # type: ignore

from ...core.exceptions import WeatherError
from .validation import require_boolean, require_mapping, require_number, require_text


def _optional_number(value, label):
    return None if value is None else require_number(value, label)


def serialize_observation(payload, now=None):
    payload = require_mapping(payload, "observación")
    observed_text = require_text(payload.get("hora_utc"), "observación.hora_utc")
    try:
        observed = datetime.fromisoformat(observed_text)
    except ValueError as exc:
        raise WeatherError("Respuesta inválida: observación.hora_utc no es una fecha") from exc
    if observed.tzinfo is None:
        raise WeatherError("Respuesta inválida: observación.hora_utc no tiene zona horaria")

    now = now or datetime.now(timezone.utc)
    age = max(0, int((now - observed).total_seconds() // 60))
    max_age = current_app.config["OBSERVATION_MAX_AGE_MIN"]

    return {
        "localidad": require_text(payload.get("localidad"), "observación.localidad"),
        "estacion": require_text(payload.get("estacion"), "observación.estacion"),
        "hora": require_text(payload.get("hora"), "observación.hora"),
        "hora_utc": observed_text,
        "antiguedad_min": age,
        "vigente": age <= max_age,
        "temp": require_number(payload.get("temp"), "observación.temp"),
        "humedad": _optional_number(payload.get("humedad"), "observación.humedad"),
        "viento_kmh": _optional_number(payload.get("viento_kmh"), "observación.viento_kmh"),
        "viento_dir": _optional_number(payload.get("viento_dir"), "observación.viento_dir"),
        "presion_hpa": _optional_number(payload.get("presion_hpa"), "observación.presion_hpa"),
        "stale": require_boolean(payload.get("stale"), "observación.stale"),
    }
