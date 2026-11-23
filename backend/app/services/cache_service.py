import json
import time
import uuid

from ..infrastructure.redis_client import get_redis


# Libera el candado solo si sigue siendo nuestro (compare-and-delete).
# Sin esto, un proceso cuyo candado expiró podría borrar el de otro.
_RELEASE_IF_OWNER = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


def read(key):
    raw = get_redis().get(key)
    return json.loads(raw) if raw else None


def write(key, data, expire_in):
    envelope = {"data": data, "saved_at": time.time()}
    get_redis().set(key, json.dumps(envelope), ex=expire_in)


def acquire_lock(key, ttl):
    """Candado corto con expiración: si el proceso muere, el candado se libera solo.

    Devuelve un token único si se adquirió, None si otro proceso lo tiene.
    """
    token = uuid.uuid4().hex
    if get_redis().set(f"{key}:lock", token, ex=ttl, nx=True):
        return token
    return None


def release_lock(key, token):
    get_redis().eval(_RELEASE_IF_OWNER, 1, f"{key}:lock", token)
