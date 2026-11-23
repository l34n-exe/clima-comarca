from flask import jsonify # type: ignore

from ...api.schemas.tide_schema import serialize_tides
from ...api.schemas.weather_schema import serialize_forecast, serialize_weather
from ...core.exceptions import WeatherError
from ...services import locations_service, weather_service
from .. import api_bp


def _respond(slug, getter, error_message, only_type=None):
    location = locations_service.get_location(slug)
    if location is None:
        return jsonify({"error": "Localidad no encontrada"}), 404
    if only_type and location["tipo"] != only_type:
        return jsonify({"error": f"Este dato solo está disponible para: {only_type}"}), 400
    try:
        return jsonify(getter(location))
    except WeatherError:
        # 500 y no 502: el frontend reintenta 502/503/504 como "servidor
        # despertando" (cold start de Render). Un fallo del proveedor no
        # se cura reintentando, así que se reporta como error de la app.
        return jsonify({"error": error_message}), 500


@api_bp.get("/weather/<slug>")
def current_weather(slug):
    return _respond(
        slug,
        lambda location: serialize_weather(weather_service.get_current(location)),
        "No se pudo obtener el clima por ahora",
    )


@api_bp.get("/forecast/<slug>")
def forecast(slug):
    return _respond(
        slug,
        lambda location: serialize_forecast(weather_service.get_forecast(location)),
        "No se pudo obtener el pronóstico por ahora",
    )


@api_bp.get("/tides/<slug>")
def tides(slug):
    return _respond(
        slug,
        lambda location: serialize_tides(weather_service.get_tides(location)),
        "No se pudieron obtener las mareas por ahora",
        only_type="playa",
    )
