from ...core.exceptions import WeatherError
from .validation import (
    require_boolean,
    require_list,
    require_mapping,
    require_number,
    require_text,
)


def serialize_tides(payload):
    payload = require_mapping(payload, "mareas")
    extremes = require_list(payload.get("mareas"), "mareas.mareas")
    series = require_list(payload.get("serie"), "mareas.serie")

    result_extremes = []
    for index, extreme in enumerate(extremes):
        extreme = require_mapping(extreme, f"mareas.mareas[{index}]")
        kind = require_text(extreme.get("tipo"), f"mareas.mareas[{index}].tipo")
        if kind not in ("pleamar", "bajamar"):
            raise WeatherError(f"Respuesta inválida: tipo de marea desconocido ({kind})")
        result_extremes.append({
            "tipo": kind,
            "hora": require_text(extreme.get("hora"), f"mareas.mareas[{index}].hora"),
            "altura_m": require_number(
                extreme.get("altura_m"), f"mareas.mareas[{index}].altura_m"
            ),
        })

    result_series = []
    for index, point in enumerate(series):
        point = require_mapping(point, f"mareas.serie[{index}]")
        result_series.append({
            "hora": require_text(point.get("hora"), f"mareas.serie[{index}].hora"),
            "altura_m": require_number(
                point.get("altura_m"), f"mareas.serie[{index}].altura_m"
            ),
        })

    return {
        "localidad": require_text(payload.get("localidad"), "mareas.localidad"),
        "mareas": result_extremes,
        "serie": result_series,
        "referencia": require_text(payload.get("referencia"), "mareas.referencia"),
        "aviso": require_text(payload.get("aviso"), "mareas.aviso"),
        "stale": require_boolean(payload.get("stale"), "mareas.stale"),
    }
