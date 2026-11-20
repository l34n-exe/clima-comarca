import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app

from ..core.exceptions import WeatherError
from . import http

KMH_PER_KNOT = 1.852
_STATION = re.compile(r"^[A-Z]{4}$")
_UTC_TIME = re.compile(r"(\d{4})\.(\d{2})\.(\d{2}) (\d{2})(\d{2}) UTC")
_TEMP = re.compile(r"^Temperature:.*\((-?\d+) C\)", re.M)
_HUMIDITY = re.compile(r"^Relative Humidity: (\d+)%", re.M)
_PRESSURE = re.compile(r"^Pressure.*\((\d+) hPa\)", re.M)
_WIND = re.compile(r"^Wind: from the \w+ \((\d{1,3}) degrees\) at \d+ MPH \((\d+) KT\)", re.M)
_WIND_VARIABLE = re.compile(r"^Wind: Variable at \d+ MPH \((\d+) KT\)", re.M)
_WIND_CALM = re.compile(r"^Wind: Calm", re.M)


def parse_decoded(text):
    when = _UTC_TIME.search(text)
    temp = _TEMP.search(text)
    if not when or not temp:
        raise WeatherError("Respuesta inesperada: la observación no tiene hora o temperatura")
    observed = datetime(*(int(part) for part in when.groups()), tzinfo=timezone.utc)

    wind_dir = wind_kmh = None
    wind = _WIND.search(text)
    variable = _WIND_VARIABLE.search(text)
    if wind:
        wind_dir = int(wind.group(1))
        wind_kmh = round(int(wind.group(2)) * KMH_PER_KNOT)
    elif variable:
        wind_kmh = round(int(variable.group(1)) * KMH_PER_KNOT)
    elif _WIND_CALM.search(text):
        wind_kmh = 0

    humidity = _HUMIDITY.search(text)
    pressure = _PRESSURE.search(text)
    local = observed.astimezone(ZoneInfo(current_app.config["TIMEZONE"]))
    return {
        "hora_utc": observed.isoformat(),
        "hora": local.strftime("%Y-%m-%dT%H:%M"),
        "temp": float(temp.group(1)),
        "humedad": float(humidity.group(1)) if humidity else None,
        "viento_kmh": wind_kmh,
        "viento_dir": wind_dir,
        "presion_hpa": float(pressure.group(1)) if pressure else None,
    }


def fetch_observation(location):
    station = location.get("estacion")
    if not isinstance(station, str) or not _STATION.match(station):
        raise WeatherError("Esta localidad no tiene una estación de observación válida")
    text = http.get(current_app.config["METAR_URL"].format(station=station)).text

    data = parse_decoded(text)
    data["localidad"] = location["nombre"]
    data["estacion"] = station
    return data
