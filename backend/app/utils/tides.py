from datetime import datetime, timedelta


def find_extremes(times, heights):
    # Busca pleamares (maximos) y bajamares (minimos) en la serie horaria.
    extremes = []
    for i in range(1, len(heights) - 1):
        y0, y1, y2 = heights[i - 1], heights[i], heights[i + 1]
        is_high = y1 > y0 and y1 >= y2
        is_low = y1 < y0 and y1 <= y2
        if not (is_high or is_low):
            continue

        denom = y0 - 2 * y1 + y2
        offset = 0.5 * (y0 - y2) / denom if denom else 0.0
        height = y1 - 0.25 * (y0 - y2) * offset
        moment = datetime.fromisoformat(times[i]) + timedelta(hours=offset)

        extremes.append({
            "tipo": "pleamar" if is_high else "bajamar",
            "hora": moment.strftime("%Y-%m-%dT%H:%M"),
            "altura_m": round(height, 2),
        })
    return extremes
