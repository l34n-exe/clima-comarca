import json
import unicodedata
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "data" / "locations.json"
_locations = None


def _normalize(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char)).lower().strip()


def all_locations():
    global _locations
    if _locations is None:
        _locations = json.loads(_FILE.read_text(encoding="utf-8"))
    return _locations


def get_location(slug):
    return next((location for location in all_locations() if location["slug"] == slug), None)


def search(query):
    query = _normalize(query)
    if not query:
        return all_locations()
    return [
        location
        for location in all_locations()
        if query in _normalize(location["nombre"])
    ]
