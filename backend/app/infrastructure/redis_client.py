import redis # type: ignore
from flask import current_app # type: ignore


def init_redis(app):
    client = app.config.get("REDIS_CLIENT")
    if client is None:
        client = redis.Redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    app.extensions["redis"] = client


def get_redis():
    return current_app.extensions["redis"]
