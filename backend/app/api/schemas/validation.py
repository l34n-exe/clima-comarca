from collections.abc import Mapping
import math

from ...core.exceptions import WeatherError


def require_mapping(value, label):
    if not isinstance(value, Mapping):
        raise WeatherError(f"Respuesta inválida: {label} debe ser un objeto")
    return value


def require_text(value, label):
    if not isinstance(value, str) or not value:
        raise WeatherError(f"Respuesta inválida: {label} debe ser texto")
    return value


def require_number(value, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise WeatherError(f"Respuesta inválida: {label} debe ser numérico")
    return value


def require_integer(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise WeatherError(f"Respuesta inválida: {label} debe ser entero")
    return value


def require_boolean(value, label):
    if not isinstance(value, bool):
        raise WeatherError(f"Respuesta inválida: {label} debe ser booleano")
    return value


def require_list(value, label):
    if not isinstance(value, list):
        raise WeatherError(f"Respuesta inválida: {label} debe ser una lista")
    return value
