import json
import time

from ..infrastructure.redis_client import get_redis


def read(key):
    raw = get_redis().get(key)
    return json.loads(raw) if raw else None


def write(key, data, expire_in):
    envelope = {"data": data, "saved_at": time.time()}
    get_redis().set(key, json.dumps(envelope), ex=expire_in)
