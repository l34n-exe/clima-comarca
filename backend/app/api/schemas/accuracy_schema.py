from ...core.exceptions import WeatherError
from .validation import (
    require_boolean,
    require_integer,
    require_list,
    require_mapping,
    require_number,
    require_text,
)


def _optional_number(value, label):
    return None if value is None else require_number(value, label)


def serialize_accuracy(payload):
    payload = require_mapping(payload, "precisión")
    days = []
    for index, day in enumerate(require_list(payload.get("por_dia"), "precisión.por_dia")):
        day = require_mapping(day, f"precisión.por_dia[{index}]")
        days.append({
            "fecha": require_text(day.get("fecha"), f"precisión.por_dia[{index}].fecha"),
            "error_c": require_number(day.get("error_c"), f"precisión.por_dia[{index}].error_c"),
            "muestras": require_integer(
                day.get("muestras"), f"precisión.por_dia[{index}].muestras"
            ),
        })

    return {
        "localidad": require_text(payload.get("localidad"), "precisión.localidad"),
        "dias": require_integer(payload.get("dias"), "precisión.dias"),
        "muestras": require_integer(payload.get("muestras"), "precisión.muestras"),
        "error_promedio_c": _optional_number(
            payload.get("error_promedio_c"), "precisión.error_promedio_c"
        ),
        "error_maximo_c": _optional_number(
            payload.get("error_maximo_c"), "precisión.error_maximo_c"
        ),
        "sesgo_c": _optional_number(payload.get("sesgo_c"), "precisión.sesgo_c"),
        "por_dia": days,
        "stale": require_boolean(payload.get("stale"), "precisión.stale"),
    }
