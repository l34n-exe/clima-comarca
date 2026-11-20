import time

from flask import current_app # type: ignore

from ..core.exceptions import WeatherError
from ..infrastructure import noaa_metar_client, open_meteo_client
from . import cache_service

# Cuánto se espera a que otro proceso termine de llenar el caché
# antes de salir a buscar el dato por nuestra cuenta
_LOCK_WAIT_SECONDS = 2.0
_LOCK_POLL_SECONDS = 0.3


def _fresh(envelope, ttl):
    return envelope and time.time() - envelope["saved_at"] < ttl


def _get_with_cache(kind, location, ttl, fetch):
    key = f"weather:{kind}:{location['slug']}"
    envelope = cache_service.read(key)

    if _fresh(envelope, ttl):
        return {**envelope["data"], "stale": False}

    locked = cache_service.acquire_lock(key, 30)
    if not locked:
        # Otro proceso está actualizando este dato: esperar a que llene el
        # caché, reintentando el candado por si se liberó
        deadline = time.monotonic() + _LOCK_WAIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(_LOCK_POLL_SECONDS)
            envelope = cache_service.read(key)
            if _fresh(envelope, ttl):
                return {**envelope["data"], "stale": False}
            locked = cache_service.acquire_lock(key, 30)
            if locked:
                break
        envelope = cache_service.read(key)

    try:
        # Releer adentro del candado: otro proceso pudo haber llenado el caché
        # entre la primera lectura y la adquisición del candado
        envelope = cache_service.read(key)
        if _fresh(envelope, ttl):
            return {**envelope["data"], "stale": False}
        try:
            data = fetch(location)
        except WeatherError:
            if envelope:
                return {**envelope["data"], "stale": True}
            raise
        cache_service.write(key, data, ttl + current_app.config["CACHE_STALE_EXTRA"])
        return {**data, "stale": False}
    finally:
        if locked:
            cache_service.release_lock(key)


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
