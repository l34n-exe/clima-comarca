import logging
import time
import uuid

from flask import Flask, g, jsonify, request #type: ignore
from flask_cors import CORS #type: ignore
from flask_limiter import Limiter #type: ignore
from werkzeug.middleware.proxy_fix import ProxyFix # type: ignore

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

    # nginx reenvía X-Forwarded-For/Proto: sin esto, Flask ve la IP del
    # proxy y no la del cliente (clave para el límite de peticiones)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    def _client_ip():
        # nginx resuelve la IP real del cliente con realip (salta Cloudflare
        # y la red interna de Render) y reenvía un único X-Forwarded-For, así
        # que el primer valor ya es confiable y no falsificable por el cliente
        xff = request.headers.get("X-Forwarded-For", "")
        first = xff.split(",")[0].strip()
        return first or request.remote_addr or "unknown"

    if not app.logger.handlers:
        app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)

    # Los hooks se registran ANTES del limiter: si el límite rechaza la
    # request, su before_request corre primero y estos igual tienen que
    # haber inicializado g.request_id/g.request_start, o el after_request
    # rompe con AttributeError y un 429 termina siendo un 500
    @app.before_request
    def _start_request():
        # Se respeta un X-Request-ID entrante para poder seguir la petición
        # a través de nginx y el frontend
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        g.request_start = time.monotonic()

    @app.after_request
    def _log_request(response):
        elapsed_ms = int((time.monotonic() - getattr(g, "request_start", time.monotonic())) * 1000)
        app.logger.info(
            "req=%s %s %s -> %s (%dms)",
            getattr(g, "request_id", "-"),
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", "-"))
        return response

    limiter = Limiter(
        key_func=_client_ip,
        default_limits=["120 per minute"],
        # Sin storage propio el límite vive en memoria de cada worker:
        # con N workers el límite efectivo se multiplica por N
        storage_uri=app.config["RATE_LIMIT_STORAGE_URI"] or "memory://",
    )
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_exceeded(_error):
        return jsonify({"error": "Demasiadas solicitudes, probá en un minuto"}), 429

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app
