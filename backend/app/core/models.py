from typing import TypedDict


class Location(TypedDict):
    nombre: str
    slug: str
    tipo: str
    lat: float
    lon: float
