from flask import jsonify

from ...core.exceptions import WeatherError
from ...services import locations_service, weather_service
from ..schemas.models_schema import serialize_models
from ..schemas.observation_schema import serialize_observation
from .. import api_bp


def _respond(slug, getter, serializer, error_message, needs_station=False):
    location = locations_service.get_location(slug)
    if location is None:
        return jsonify({"error": "Localidad no encontrada"}), 404
    if needs_station and not location.get("estacion"):
        return jsonify({"error": "Esta localidad no tiene estación de observación"}), 404
    try:
        return jsonify(serializer(getter(location)))
    except WeatherError:
        return jsonify({"error": error_message}), 502


@api_bp.get("/models/<slug>")
def models(slug):
    return _respond(
        slug,
        weather_service.get_models,
        serialize_models,
        "No se pudo obtener la comparación de modelos por ahora",
    )


@api_bp.get("/observation/<slug>")
def observation(slug):
    return _respond(
        slug,
        weather_service.get_observation,
        serialize_observation,
        "No se pudo obtener la observación por ahora",
        needs_station=True,
    )
