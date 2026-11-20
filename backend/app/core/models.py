from typing import NotRequired, TypedDict


class Location(TypedDict):
    nombre: str
    slug: str
    tipo: str
    lat: float
    lon: float
    estacion: NotRequired[str]
