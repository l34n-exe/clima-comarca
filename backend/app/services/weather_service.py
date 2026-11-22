import time

from flask import current_app # type: ignore

from ..core.exceptions import WeatherError
from ..infrastructure import met_norway_client, noaa_metar_client, open_meteo_client
from . import cache_service

# Cuánto se espera a que otro proceso termine de llenar el caché
# antes de salir a buscar el dato por nuestra cuenta
_LOCK_WAIT_SECONDS = 2.0
_LOCK_POLL_SECONDS = 0.3

# Versión del formato cacheado del pronóstico: subirla cuando cambie la
# forma de los datos (campos nuevos, renombres, semántica) para invalidar
# entradas viejas que ya no tienen la estructura esperada
FORECAST_CACHE_VERSION = 3


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


def _with_fallback(primary, fallback):
    """Si el proveedor principal falla (p. ej. Open-Meteo rate-limita la IP
    del hosting), se intenta el respaldo. Si los dos fallan, se propaga el
    error del respaldo."""

    def fetch(location):
        try:
            data = primary(location)
            data["fuente"] = "open-meteo"
            return data
        except WeatherError as exc:
            current_app.logger.warning(
                "Proveedor principal falló para %s, usando MET Norway: %s",
                location["slug"],
                exc,
            )
            data = fallback(location)
            data["fuente"] = "met-norway"
            return data

    return fetch


def get_current(location):
    return _get_with_cache(
        "current",
        location,
        current_app.config["CACHE_TTL_CURRENT"],
        _with_fallback(open_meteo_client.fetch_current, met_norway_client.fetch_current),
    )


def get_forecast(location):
    return _get_with_cache(
        f"forecast-v{FORECAST_CACHE_VERSION}",
        location,
        current_app.config["CACHE_TTL_FORECAST"],
        _with_fallback(open_meteo_client.fetch_forecast, met_norway_client.fetch_forecast),
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
