def serialize_location(location):
    return {
        "nombre": location["nombre"],
        "slug": location["slug"],
        "tipo": location["tipo"],
        "lat": location["lat"],
        "lon": location["lon"],
        "observacion": bool(location.get("estacion")),
    }


def serialize_locations(locations):
    return [serialize_location(location) for location in locations]
