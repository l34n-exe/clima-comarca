from flask import Flask #type: ignore
from flask_cors import CORS #type: ignore

from .config import Config
from .extensions import init_redis


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    # Los tests pasan su propia config (por ejemplo un Redis falso)
    if overrides:
        app.config.update(overrides)
    Config.validate(app.config)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    init_redis(app)

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app
