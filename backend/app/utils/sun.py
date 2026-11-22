import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def sunrise_sunset(day: date, lat: float, lon: float, tz_name):
    """Amanecer y atardecer locales ("HH:MM") con la aproximación NOAA.

    Error típico de 1-2 minutos: sobra para mostrar horarios de luz.
    """
    n = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (n - 1 + 0.5)  # mediodía UTC aprox
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    lat_r = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(lat_r) * math.cos(decl)) - math.tan(
        lat_r
    ) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None, None  # día polar
    ha = math.degrees(math.acos(cos_ha))
    rise_utc = 720 - 4 * (lon + ha) - eqtime
    set_utc = 720 - 4 * (lon - ha) - eqtime
    tz = ZoneInfo(tz_name)

    def local_hhmm(minutes_utc):
        dt = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes_utc)
        return dt.astimezone(tz).strftime("%H:%M")

    return local_hhmm(rise_utc), local_hhmm(set_utc)
