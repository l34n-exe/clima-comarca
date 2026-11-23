from flask import jsonify, request # type: ignore

from ...api.schemas.location_schema import serialize_locations
from ...services.locations_service import search
from .. import api_bp


@api_bp.get("/locations")
def list_locations():
    query = request.args.get("q", "")
    return jsonify(serialize_locations(search(query)))
