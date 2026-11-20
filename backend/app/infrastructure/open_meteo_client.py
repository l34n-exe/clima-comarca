import math
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app # type: ignore

from ..core.exceptions import WeatherError
from ..utils.tides import find_extremes
from . import http


WEATHER_CODES = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna leve", 53: "Llovizna", 55: "Llovizna intensa",
    56: "Llovizna helada leve", 57: "Llovizna helada intensa",
    61: "Lluvia leve", 63: "Lluvia", 65: "Lluvia intensa",
    66: "Lluvia helada leve", 67: "Lluvia helada intensa",
    71: "Nevada leve", 73: "Nevada", 75: "Nevada intensa",
    77: "Granos de nieve",
    80: "Chaparrones leves", 81: "Chaparrones", 82: "Chaparrones fuertes",
    85: "Chaparrones de nieve leves", 86: "Chaparrones de nieve fuertes",
    95: "Tormenta", 96: "Tormenta con granizo", 99: "Tormenta fuerte con granizo",
}


def _describe(code):
    return WEATHER_CODES.get(code, "Sin datos")


def _is_number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _require_number(value, field):
    if not _is_number(value):
        raise WeatherError(f"Respuesta inesperada: {field} no es un número válido")


def _require_integer(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise WeatherError(f"Respuesta inesperada: {field} no es un entero válido")


def _request(url, params):
    try:
        return http.get(url, params).json()
    except ValueError as exc:
        raise WeatherError(str(exc)) from exc


def fetch_current(location):
    raw = _request(current_app.config["WEATHER_API_URL"], {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "wind_speed_10m,wind_gusts_10m,wind_direction_10m,weather_code",
        "timezone": current_app.config["TIMEZONE"],
    })
    try:
        c = raw["current"]
        if not isinstance(c, dict):
            raise WeatherError("Respuesta inesperada: current no es un objeto")
        numeric_fields = (
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
        )
        for field in numeric_fields:
            _require_number(c[field], f"current.{field}")
        gusts = c.get("wind_gusts_10m")
        if gusts is not None:
            _require_number(gusts, "current.wind_gusts_10m")
        _require_integer(c["weather_code"], "current.weather_code")
        if not isinstance(c["time"], str) or not c["time"]:
            raise WeatherError("Respuesta inesperada: current.time no es válido")
        return {
            "localidad": location["nombre"],
            "temp": c["temperature_2m"],
            "sensacion": c["apparent_temperature"],
            "humedad": c["relative_humidity_2m"],
            "viento_kmh": c["wind_speed_10m"],
            "rafaga_kmh": gusts,
            "viento_dir": c["wind_direction_10m"],
            "codigo": c["weather_code"],
            "descripcion": _describe(c["weather_code"]),
            "hora": c["time"],
        }
    except (KeyError, TypeError) as exc:
        raise WeatherError(f"Respuesta inesperada: falta {exc}") from exc


def fetch_forecast(location):
    raw = _request(current_app.config["WEATHER_API_URL"], {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_sum,precipitation_probability_max,wind_speed_10m_max,"
                 "wind_gusts_10m_max,sunrise,sunset",
        "hourly": "temperature_2m,wind_speed_10m,wind_gusts_10m,"
                  "precipitation_probability",
        "forecast_days": 7,
        "timezone": current_app.config["TIMEZONE"],
    })
    try:
        d = raw["daily"]
        if not isinstance(d, dict):
            raise WeatherError("Respuesta inesperada: daily no es un objeto")
        fields = (
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
        )
        dates = d["time"]
        if not isinstance(dates, list) or not all(
            isinstance(day, str) and day for day in dates
        ):
            raise WeatherError("Respuesta inesperada: daily.time no es una lista válida")
        for field in fields:
            values = d[field]
            if not isinstance(values, list) or len(values) != len(dates):
                raise WeatherError(
                    f"Respuesta inesperada: daily.{field} no coincide con daily.time"
                )
            for value in values:
                _require_number(value, f"daily.{field}")
        if not isinstance(d["weather_code"], list) or len(d["weather_code"]) != len(dates):
            raise WeatherError(
                "Respuesta inesperada: daily.weather_code no coincide con daily.time"
            )
        for value in d["weather_code"]:
            _require_integer(value, "daily.weather_code")
        for field in ("sunrise", "sunset"):
            values = d[field]
            if not isinstance(values, list) or len(values) != len(dates) or not all(
                isinstance(value, str) and value for value in values
            ):
                raise WeatherError(
                    f"Respuesta inesperada: daily.{field} no coincide con daily.time"
                )
        days = [
            {
                "fecha": dates[i],
                "max": d["temperature_2m_max"][i],
                "min": d["temperature_2m_min"][i],
                "lluvia_mm": d["precipitation_sum"][i],
                "prob_lluvia": d["precipitation_probability_max"][i],
                "viento_max_kmh": d["wind_speed_10m_max"][i],
                "rafaga_max_kmh": d["wind_gusts_10m_max"][i],
                "amanecer": d["sunrise"][i],
                "atardecer": d["sunset"][i],
                "codigo": d["weather_code"][i],
                "descripcion": _describe(d["weather_code"][i]),
            }
            for i in range(len(d["time"]))
        ]
        hourly = raw["hourly"]
        if not isinstance(hourly, dict):
            raise WeatherError("Respuesta inesperada: hourly no es un objeto")
        times = hourly["time"]
        hourly_fields = (
            "temperature_2m",
            "wind_speed_10m",
            "wind_gusts_10m",
            "precipitation_probability",
        )
        if not isinstance(times, list) or not all(
            isinstance(value, str) and value for value in times
        ):
            raise WeatherError("Respuesta inesperada: hourly.time no es una lista válida")
        for field in hourly_fields:
            values = hourly[field]
            if not isinstance(values, list) or len(values) != len(times):
                raise WeatherError(
                    f"Respuesta inesperada: hourly.{field} no coincide con hourly.time"
                )
            for value in values:
                _require_number(value, f"hourly.{field}")
        start = datetime.now(ZoneInfo(current_app.config["TIMEZONE"])).replace(
            tzinfo=None, minute=0, second=0, microsecond=0
        )
        try:
            parsed_times = [datetime.fromisoformat(value) for value in times]
        except ValueError as exc:
            raise WeatherError("Respuesta inesperada: formato de hora por hora inválido") from exc
        start_index = next(
            (index for index, value in enumerate(parsed_times) if value >= start),
            None,
        )
        if start_index is None or len(times) - start_index < 24:
            raise WeatherError("Respuesta inesperada: no hay 24 horas de pronóstico disponibles")
        hourly_forecast = [
            {
                "hora": times[index],
                "temp": hourly["temperature_2m"][index],
                "viento_kmh": hourly["wind_speed_10m"][index],
                "rafaga_kmh": hourly["wind_gusts_10m"][index],
                "prob_lluvia": hourly["precipitation_probability"][index],
            }
            for index in range(start_index, start_index + 24)
        ]
        return {
            "localidad": location["nombre"],
            "dias": days,
            "horas": hourly_forecast,
        }
    except (KeyError, IndexError, TypeError) as exc:
        raise WeatherError(f"Respuesta inesperada: {exc}") from exc


def fetch_tides(location):
    raw = _request(current_app.config["MARINE_API_URL"], {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "hourly": "sea_level_height_msl",
        "forecast_days": 3,
        "timezone": current_app.config["TIMEZONE"],
    })
    try:
        hourly = raw["hourly"]
        if not isinstance(hourly, dict):
            raise WeatherError("Respuesta inesperada: hourly no es un objeto")
        times = hourly["time"]
        heights = hourly["sea_level_height_msl"]
    except (KeyError, TypeError) as exc:
        raise WeatherError(f"Respuesta inesperada: falta {exc}") from exc

    if (
        not isinstance(times, list)
        or not isinstance(heights, list)
        or len(times) != len(heights)
        or len(times) < 3
    ):
        raise WeatherError("Respuesta inesperada: serie de mareas inválida")
    if not all(isinstance(time, str) and time for time in times):
        raise WeatherError("Respuesta inesperada: horarios de marea inválidos")
    try:
        for time in times:
            datetime.fromisoformat(time)
    except ValueError as exc:
        raise WeatherError("Respuesta inesperada: formato de hora de marea inválido") from exc
    if any(not _is_number(height) for height in heights):
        raise WeatherError("Sin datos de marea para esta ubicación")

    return {
        "localidad": location["nombre"],
        "mareas": find_extremes(times, heights),
        "serie": [{"hora": time, "altura_m": round(height, 2)} for time, height in zip(times, heights)],
        "referencia": "nivel medio del mar",
        "aviso": "Estimación de un modelo global (~8 km), no oficial. Los horarios pueden "
                 "diferir en alrededor de una hora y las alturas no coinciden con las tablas "
                 "oficiales. No sirve para navegar.",
    }


MODEL_LABELS = {
    "ecmwf_ifs025": "ECMWF",
    "gfs_global": "GFS (NOAA)",
    "icon_global": "ICON (DWD)",
    "gem_global": "GEM (Canadá)",
}


def _model_series(daily, key, model, dates):
    values = daily.get(f"{key}_{model}")
    if (
        not isinstance(values, list)
        or len(values) != len(dates)
        or not all(_is_number(value) for value in values)
    ):
        return None
    return values


def fetch_models(location):
    models = current_app.config["WEATHER_MODELS"]
    raw = _request(current_app.config["WEATHER_API_URL"], {
        "latitude": location["lat"],
        "longitude": location["lon"],
        "daily": "temperature_2m_max,temperature_2m_min",
        "models": ",".join(models),
        "forecast_days": 7,
        "timezone": current_app.config["TIMEZONE"],
    })
    try:
        daily = raw["daily"]
        if not isinstance(daily, dict):
            raise WeatherError("Respuesta inesperada: daily no es un objeto")
        dates = daily["time"]
    except (KeyError, TypeError) as exc:
        raise WeatherError(f"Respuesta inesperada: falta {exc}") from exc
    if not isinstance(dates, list) or not dates or not all(
        isinstance(day, str) and day for day in dates
    ):
        raise WeatherError("Respuesta inesperada: daily.time no es una lista válida")

    usable = []
    for model in models:
        highs = _model_series(daily, "temperature_2m_max", model, dates)
        lows = _model_series(daily, "temperature_2m_min", model, dates)
        if highs is not None and lows is not None:
            usable.append((model, highs, lows))
    if len(usable) < 2:
        raise WeatherError("Respuesta inesperada: menos de dos modelos con datos completos")

    return {
        "localidad": location["nombre"],
        "modelos": [{"id": model, "nombre": MODEL_LABELS.get(model, model)} for model, _, _ in usable],
        "dias": [
            {
                "fecha": dates[index],
                "modelos": [
                    {"modelo": model, "max": highs[index], "min": lows[index]}
                    for model, highs, lows in usable
                ],
            }
            for index in range(len(dates))
        ],
    }
