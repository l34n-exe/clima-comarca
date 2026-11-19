import time

from flask import current_app # type: ignore

from ..core.exceptions import WeatherError
from ..infrastructure import noaa_metar_client, open_meteo_client
from . import cache_service


def _get_with_cache(kind, location, ttl, fetch):
    key = f"weather:{kind}:{location['slug']}"
    envelope = cache_service.read(key)

    if envelope and time.time() - envelope["saved_at"] < ttl:
        return {**envelope["data"], "stale": False}

    try:
        data = fetch(location)
    except WeatherError:
        if envelope:
            return {**envelope["data"], "stale": True}
        raise

    cache_service.write(key, data, ttl + current_app.config["CACHE_STALE_EXTRA"])
    return {**data, "stale": False}


def get_current(location):
    return _get_with_cache(
        "current",
        location,
        current_app.config["CACHE_TTL_CURRENT"],
        open_meteo_client.fetch_current,
    )


def get_forecast(location):
    return _get_with_cache(
        "forecast-v2",
        location,
        current_app.config["CACHE_TTL_FORECAST"],
        open_meteo_client.fetch_forecast,
    )


def get_tides(location):
    return _get_with_cache(
        "tides",
        location,
        current_app.config["CACHE_TTL_TIDES"],
        open_meteo_client.fetch_tides,
    )


def get_models(location):
    return _get_with_cache(
        "models",
        location,
        current_app.config["CACHE_TTL_FORECAST"],
        open_meteo_client.fetch_models,
    )


def get_observation(location):
    return _get_with_cache(
        "observation",
        location,
        current_app.config["CACHE_TTL_OBSERVATION"],
        noaa_metar_client.fetch_observation,
    )
