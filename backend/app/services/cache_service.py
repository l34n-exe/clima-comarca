import json
import time

from ..infrastructure.redis_client import get_redis


def read(key):
    raw = get_redis().get(key)
    return json.loads(raw) if raw else None


def write(key, data, expire_in):
    envelope = {"data": data, "saved_at": time.time()}
    get_redis().set(key, json.dumps(envelope), ex=expire_in)


def acquire_lock(key, ttl):
    """Candado corto con expiración: si el proceso muere, el candado se libera solo."""
    return bool(get_redis().set(f"{key}:lock", "1", ex=ttl, nx=True))


def release_lock(key):
    get_redis().delete(f"{key}:lock")
