from ...core.exceptions import WeatherError
from .validation import (
    require_boolean,
    require_integer,
    require_list,
    require_mapping,
    require_number,
    require_text,
)


_CURRENT_NUMBERS = ("temp", "sensacion", "humedad", "viento_kmh", "viento_dir")
_FORECAST_NUMBERS = (
    "max", "min", "lluvia_mm", "prob_lluvia", "viento_max_kmh",
)


def _optional_text(value):
    return value if isinstance(value, str) and value else None


def serialize_weather(payload):
    payload = require_mapping(payload, "clima")
    result = {
        "localidad": require_text(payload.get("localidad"), "clima.localidad"),
        "codigo": require_integer(payload.get("codigo"), "clima.codigo"),
        "descripcion": require_text(payload.get("descripcion"), "clima.descripcion"),
        "hora": require_text(payload.get("hora"), "clima.hora"),
        "stale": require_boolean(payload.get("stale"), "clima.stale"),
    }
    for field in _CURRENT_NUMBERS:
        result[field] = require_number(payload.get(field), f"clima.{field}")
    gusts = payload.get("rafaga_kmh")
    result["rafaga_kmh"] = (
        None if gusts is None else require_number(gusts, "clima.rafaga_kmh")
    )
    result["fuente"] = _optional_text(payload.get("fuente"))
    return result


def serialize_forecast(payload):
    payload = require_mapping(payload, "pronóstico")
    days = require_list(payload.get("dias"), "pronóstico.dias")
    result_days = []
    for index, day in enumerate(days):
        day = require_mapping(day, f"pronóstico.dias[{index}]")
        result_day = {
            "fecha": require_text(day.get("fecha"), f"pronóstico.dias[{index}].fecha"),
            "codigo": require_integer(day.get("codigo"), f"pronóstico.dias[{index}].codigo"),
            "descripcion": require_text(
                day.get("descripcion"), f"pronóstico.dias[{index}].descripcion"
            ),
        }
        for field in _FORECAST_NUMBERS:
            result_day[field] = require_number(
                day.get(field), f"pronóstico.dias[{index}].{field}"
            )
        gust = day.get("rafaga_max_kmh")
        result_day["rafaga_max_kmh"] = (
            None if gust is None else require_number(gust, f"pronóstico.dias[{index}].rafaga_max_kmh")
        )
        for field in ("amanecer", "atardecer"):
            result_day[field] = require_text(
                day.get(field), f"pronóstico.dias[{index}].{field}"
            )
        result_days.append(result_day)

    hours = require_list(payload.get("horas"), "pronóstico.horas")
    if len(hours) != 24:
        raise WeatherError("Respuesta inválida: pronóstico.horas debe contener 24 horas")
    result_hours = []
    for index, hour in enumerate(hours):
        hour = require_mapping(hour, f"pronóstico.horas[{index}]")
        result_hour = {
            "hora": require_text(hour.get("hora"), f"pronóstico.horas[{index}].hora"),
        }
        for field in ("temp", "viento_kmh", "prob_lluvia"):
            result_hour[field] = require_number(
                hour.get(field), f"pronóstico.horas[{index}].{field}"
            )
        gust = hour.get("rafaga_kmh")
        result_hour["rafaga_kmh"] = (
            None if gust is None else require_number(gust, f"pronóstico.horas[{index}].rafaga_kmh")
        )
        result_hours.append(result_hour)

    return {
        "localidad": require_text(payload.get("localidad"), "pronóstico.localidad"),
        "dias": result_days,
        "horas": result_hours,
        "stale": require_boolean(payload.get("stale"), "pronóstico.stale"),
        "fuente": _optional_text(payload.get("fuente")),
    }
