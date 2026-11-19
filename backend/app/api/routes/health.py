import redis as redis_lib # type: ignore
from flask import jsonify # type: ignore

from ...infrastructure.redis_client import get_redis
from .. import api_bp


@api_bp.get("/health")
def health():
    try:
        get_redis().ping()
        redis_ok = True
    except redis_lib.RedisError:
        redis_ok = False

    status = 200 if redis_ok else 503
    return jsonify({"status": "ok" if redis_ok else "degraded", "redis": redis_ok}), status
