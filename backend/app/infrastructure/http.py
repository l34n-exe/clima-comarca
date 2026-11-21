import time

import requests
from flask import current_app

from ..core.exceptions import WeatherError


def _retryable(exc):
    # 4xx es culpa del pedido: reintentar no cambia nada. 5xx, 429 (rate limit)
    # y fallos de red/conexión sí pueden ser transitorios.
    if not isinstance(exc, requests.HTTPError):
        return True
    status = exc.response.status_code if exc.response is not None else 0
    return status >= 500 or status == 429


def get(url, params=None):
    """GET con timeout, reintentos y backoff exponencial ante fallos transitorios."""
    timeout = current_app.config["HTTP_TIMEOUT"]
    retries = current_app.config["HTTP_RETRIES"]
    backoff = current_app.config["HTTP_RETRY_BACKOFF"]
    error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            error = exc
            if not _retryable(exc):
                break
            # Ante 429 el proveedor suele indicar cuánto esperar
            wait = backoff * (2**attempt)
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                headers = getattr(exc.response, "headers", None) or {}
                retry_after = headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = max(wait, min(int(retry_after), 10))
            if attempt < retries - 1:
                time.sleep(wait)
            continue
        if attempt < retries - 1:
            time.sleep(backoff * (2**attempt))
    current_app.logger.warning("Proveedor inaccesible tras %s intentos: %s %s", retries, url, error)
    raise WeatherError(str(error)) from error
