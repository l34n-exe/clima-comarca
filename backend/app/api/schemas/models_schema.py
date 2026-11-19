from ...core.exceptions import WeatherError
from .validation import require_boolean, require_list, require_mapping, require_number, require_text


def serialize_models(payload):
    payload = require_mapping(payload, "modelos")
    models = []
    for index, model in enumerate(require_list(payload.get("modelos"), "modelos.modelos")):
        model = require_mapping(model, f"modelos.modelos[{index}]")
        models.append({
            "id": require_text(model.get("id"), f"modelos.modelos[{index}].id"),
            "nombre": require_text(model.get("nombre"), f"modelos.modelos[{index}].nombre"),
        })
    known = {model["id"] for model in models}

    days = []
    for index, day in enumerate(require_list(payload.get("dias"), "modelos.dias")):
        day = require_mapping(day, f"modelos.dias[{index}]")
        entries = []
        for j, entry in enumerate(require_list(day.get("modelos"), f"modelos.dias[{index}].modelos")):
            label = f"modelos.dias[{index}].modelos[{j}]"
            entry = require_mapping(entry, label)
            model_id = require_text(entry.get("modelo"), f"{label}.modelo")
            if model_id not in known:
                raise WeatherError(f"Respuesta inválida: modelo desconocido ({model_id})")
            entries.append({
                "modelo": model_id,
                "max": require_number(entry.get("max"), f"{label}.max"),
                "min": require_number(entry.get("min"), f"{label}.min"),
            })
        days.append({
            "fecha": require_text(day.get("fecha"), f"modelos.dias[{index}].fecha"),
            "modelos": entries,
        })

    return {
        "localidad": require_text(payload.get("localidad"), "modelos.localidad"),
        "modelos": models,
        "dias": days,
        "stale": require_boolean(payload.get("stale"), "modelos.stale"),
    }
