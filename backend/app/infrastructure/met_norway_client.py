from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app # type: ignore

from ..core.exceptions import WeatherError
from ..utils.sun import sunrise_sunset
from . import http

API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
# MET Norway exige un User-Agent identificable con contacto del proyecto
USER_AGENT = "clima-comarca/1.0 https://github.com/l34n-exe/clima-comarca"

# Símbolos de MET Norway → códigos WMO (los mismos que usa la app)
SYMBOL_TO_WMO = {
    "clearsky_day": 0, "clearsky_night": 0,
    "fair_day": 1, "fair_night": 1,
    "partlycloudy_day": 2, "partlycloudy_night": 2,
    "cloudy": 3, "fog": 45, "lightrainshowers_day": 80, "lightrainshowers_night": 80,
    "rainshowers_day": 81, "rainshowers_night": 81,
    "heavyrainshowers_day": 82, "heavyrainshowers_night": 82,
    "lightrain": 61, "rain": 63, "heavyrain": 65,
    "rainandthunder": 95, "sleet": 66, "snow": 71, "heavysnow": 75,
    "snowshowers_day": 73, "snowshowers_night": 73,
    "lightrainandthunder": 95, "rainandthunder_day": 95, "rainandthunder_night": 95,
}


def _require(mapping, field):
    value = mapping.get(field) if isinstance(mapping, dict) else None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise WeatherError(f"Respuesta inesperada de MET Norway: falta {field}")
    return value


def _entries(location):
    try:
        raw = http.get(
            API_URL,
            {"lat": round(location["lat"], 4), "lon": round(location["lon"], 4)},
            headers={"User-Agent": USER_AGENT},
        ).json()
        timeseries = raw["properties"]["timeseries"]
        if not isinstance(timeseries, list) or not timeseries:
            raise WeatherError("Respuesta inesperada de MET Norway: sin timeseries")
        return timeseries
    except (KeyError, TypeError) as exc:
        raise WeatherError(f"Respuesta inesperada de MET Norway: {exc}") from exc


def _instant(entry):
    return entry.get("data", {}).get("instant", {}).get("details", {})


def _next_hour(entry):
    return entry.get("data", {}).get("next_1_hours", {})


def _symbol(entry):
    data = entry.get("data", {})
    # Las primeras ~60 h tienen next_1_hours; después la serie se espacia y
    # el símbolo viene en next_6_hours / next_12_hours
    for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
        code = data.get(period, {}).get("summary", {}).get("symbol_code")
        if code:
            return SYMBOL_TO_WMO.get(code, 3), code
    return 3, ""


def _precipitation(entry):
    data = entry.get("data", {})
    # next_1_hours es mm en 1 h; next_6_hours/next_12_hours son acumulados
    # del período que arranca en la hora del entry (las entradas espaciadas
    # 6 h/12 h no se solapan, así que sumar da el total del día)
    for period in ("next_1_hours", "next_6_hours", "next_12_hours"):
        value = data.get(period, {}).get("details", {}).get("precipitation_amount")
        if value is not None:
            return value
    return 0.0


def _local_time(iso_utc):
    tz = ZoneInfo(current_app.config["TIMEZONE"])
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(tz)
    return dt.strftime("%Y-%m-%dT%H:%M"), dt.date().isoformat()


def fetch_current(location):
    # La serie cubre ~10 días: se usa la entrada más cercana a ahora,
    # no la última (que está en el futuro)
    tz = ZoneInfo(current_app.config["TIMEZONE"])
    now = datetime.now(tz)
    entries = _entries(location)

    def entry_dt(entry):
        return datetime.fromisoformat(entry["time"].replace("Z", "+00:00")).astimezone(tz)

    # La serie es un pronóstico horario: la entrada más cercana a ahora
    # puede ser una hora futura. Para el clima "actual" se prefiere la
    # última hora ya ocurrida; solo si no hay ninguna pasada se usa la
    # más cercana (así `hora` nunca queda en el futuro).
    past = [e for e in entries if entry_dt(e) <= now]
    if past:
        entry = max(past, key=entry_dt)
    else:
        entry = min(entries, key=lambda e: abs((entry_dt(e) - now).total_seconds()))
    instant = _instant(entry)
    code, _ = _symbol(entry)
    wind_ms = _require(instant, "wind_speed")
    hora, _ = _local_time(entry["time"])
    return {
        "localidad": location["nombre"],
        "temp": _require(instant, "air_temperature"),
        "sensacion": _require(instant, "air_temperature"),
        "humedad": _require(instant, "relative_humidity"),
        "viento_kmh": wind_ms * 3.6,
        "rafaga_kmh": None,
        "viento_dir": _require(instant, "wind_from_direction"),
        "codigo": code,
        "descripcion": _describe_wmo(code),
        "hora": hora,
    }


def _describe_wmo(code):
    from .open_meteo_client import WEATHER_CODES

    return WEATHER_CODES.get(code, "Sin datos")


def fetch_forecast(location):
    entries = _entries(location)
    tz = ZoneInfo(current_app.config["TIMEZONE"])
    now = datetime.now(tz).replace(tzinfo=None, minute=0, second=0, microsecond=0)

    hourly = []
    for entry in entries:
        local, _ = _local_time(entry["time"])
        dt = datetime.fromisoformat(local)
        if dt < now:
            continue
        instant = _instant(entry)
        precip = _precipitation(entry)
        wind_kmh = _require(instant, "wind_speed") * 3.6
        code, _ = _symbol(entry)
        hourly.append({
            "dt": dt,
            "hora": local,
            "temp": _require(instant, "air_temperature"),
            "viento_kmh": wind_kmh,
            # MET Norway no informa ráfagas: null, no un valor de relleno
            "rafaga_kmh": None,
            "prob_lluvia": 100.0 if precip >= 0.1 else 0.0,
            "codigo": code,
            "precip_mm": precip,
        })
        if len(hourly) >= 24:
            break
    if len(hourly) < 24:
        raise WeatherError("Respuesta inesperada de MET Norway: menos de 24 horas")

    by_day = {}
    for h in hourly:
        by_day.setdefault(h["dt"].date(), []).append(h)
    # Agregar días completos desde la serie completa (no solo las primeras 24 h)
    all_days = {}
    for entry in entries:
        local, _ = _local_time(entry["time"])
        dt = datetime.fromisoformat(local)
        instant = _instant(entry)
        precip = _precipitation(entry)
        wind_kmh = _require(instant, "wind_speed") * 3.6
        all_days.setdefault(dt.date(), []).append({
            "temp": _require(instant, "air_temperature"),
            "precip_mm": precip,
            "viento_kmh": wind_kmh,
            "codigo": _symbol(entry)[0],
        })

    days = []
    for day in sorted(all_days)[:7]:
        points = all_days[day]
        temps = [p["temp"] for p in points]
        precip_sum = sum(p["precip_mm"] for p in points)
        winds = [p["viento_kmh"] for p in points]
        sunrise, sunset = sunrise_sunset(day, location["lat"], location["lon"], current_app.config["TIMEZONE"])
        code = points[0]["codigo"]
        # El frontend espera ISO completo (como Open-Meteo), no solo "HH:MM"
        amanecer = f"{day.isoformat()}T{sunrise}" if sunrise else ""
        atardecer = f"{day.isoformat()}T{sunset}" if sunset else ""
        days.append({
            "fecha": day.isoformat(),
            "max": max(temps),
            "min": min(temps),
            "lluvia_mm": round(precip_sum, 1),
            "prob_lluvia": 100.0 if precip_sum >= 0.5 else 0.0,
            "viento_max_kmh": max(winds),
            "rafaga_max_kmh": None,
            "amanecer": amanecer,
            "atardecer": atardecer,
            "codigo": code,
            "descripcion": _describe_wmo(code),
        })

    return {
        "localidad": location["nombre"],
        "dias": days,
        "horas": [
            {k: h[k] for k in ("hora", "temp", "viento_kmh", "rafaga_kmh", "prob_lluvia")}
            for h in hourly
        ],
    }
