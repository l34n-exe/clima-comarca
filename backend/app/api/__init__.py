from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Las rutas se importan al final para registrarse en el blueprint.
from .routes import health, locations, sources, weather  # noqa: E402,F401
