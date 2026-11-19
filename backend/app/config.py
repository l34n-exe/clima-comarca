import os


def _integer_env(name, default):
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un número entero") from exc


class Config:
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # Cuánto tiempo (en segundos) un dato se considera fresco
    CACHE_TTL_CURRENT = _integer_env("CACHE_TTL_CURRENT", 600)
    CACHE_TTL_FORECAST = _integer_env("CACHE_TTL_FORECAST", 3600)
    # Las mareas se calculan por modelo y cambian poco: se cachean más tiempo
    CACHE_TTL_TIDES = _integer_env("CACHE_TTL_TIDES", 21600)
    CACHE_TTL_OBSERVATION = _integer_env("CACHE_TTL_OBSERVATION", 600)
    # Tiempo extra que se guarda el dato viejo, por si la API externa falla
    CACHE_STALE_EXTRA = _integer_env("CACHE_STALE_EXTRA", 86400)

    # API externa del clima (Open-Meteo)
    WEATHER_API_URL = os.getenv("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")
    WEATHER_MODELS = tuple(
        model.strip()
        for model in os.getenv(
            "WEATHER_MODELS",
            "ecmwf_ifs025,gfs_global,icon_global,gem_global",
        ).split(",")
        if model.strip()
    )
    # API marina de Open-Meteo (de acá salen las mareas)
    MARINE_API_URL = os.getenv("MARINE_API_URL", "https://marine-api.open-meteo.com/v1/marine")
    METAR_URL = os.getenv(
        "METAR_URL",
        "https://tgftp.nws.noaa.gov/data/observations/metar/decoded/{station}.TXT",
    )
    OBSERVATION_MAX_AGE_MIN = _integer_env("OBSERVATION_MAX_AGE_MIN", 180)
    TIMEZONE = "America/Argentina/Buenos_Aires"
    HTTP_TIMEOUT = _integer_env("HTTP_TIMEOUT", 8)

    @staticmethod
    def validate(config):
        for name in (
            "CACHE_TTL_CURRENT",
            "CACHE_TTL_FORECAST",
            "CACHE_TTL_TIDES",
            "CACHE_TTL_OBSERVATION",
            "CACHE_STALE_EXTRA",
            "OBSERVATION_MAX_AGE_MIN",
        ):
            if isinstance(config[name], bool) or not isinstance(config[name], int):
                raise ValueError(f"{name} debe ser un número entero")
            if config[name] < 0:
                raise ValueError(f"{name} no puede ser negativo")
        if isinstance(config["HTTP_TIMEOUT"], bool) or not isinstance(
            config["HTTP_TIMEOUT"], int
        ):
            raise ValueError("HTTP_TIMEOUT debe ser un número entero")
        if config["HTTP_TIMEOUT"] <= 0:
            raise ValueError("HTTP_TIMEOUT debe ser mayor que cero")
        if not isinstance(config["WEATHER_MODELS"], (list, tuple)):
            raise ValueError("WEATHER_MODELS debe ser una lista de modelos")
        if len(config["WEATHER_MODELS"]) < 2:
            raise ValueError("WEATHER_MODELS debe incluir al menos 2 modelos")
        if not all(isinstance(model, str) and model.strip() for model in config["WEATHER_MODELS"]):
            raise ValueError("Cada modelo de WEATHER_MODELS debe tener texto")
        if not isinstance(config["METAR_URL"], str) or "{station}" not in config["METAR_URL"]:
            raise ValueError("METAR_URL debe contener el marcador {station}")
        if config["OBSERVATION_MAX_AGE_MIN"] <= 0:
            raise ValueError("OBSERVATION_MAX_AGE_MIN debe ser mayor que cero")

        origins = config["CORS_ORIGINS"]
        if isinstance(origins, str):
            origins = origins.split(",")
        if not isinstance(origins, (list, tuple)):
            raise ValueError("CORS_ORIGINS debe ser texto o una lista de orígenes")
        if not all(isinstance(origin, str) for origin in origins):
            raise ValueError("Cada origen de CORS_ORIGINS debe ser texto")
        config["CORS_ORIGINS"] = [
            origin.strip() for origin in origins if origin.strip()
        ]
