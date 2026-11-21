import time

import requests
from flask import current_app

from ..core.exceptions import WeatherError


def _retryable(exc):
    # 4xx es culpa del pedido: reintentar no cambia nada. 5xx y fallos
    # de red/conexión sí pueden ser transitorios.
    return not isinstance(exc, requests.HTTPError) or (
        exc.response is not None and exc.response.status_code >= 500
    )


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
        if attempt < retries - 1:
            time.sleep(backoff * (2**attempt))
    current_app.logger.warning("Proveedor inaccesible tras %s intentos: %s %s", retries, url, error)
    raise WeatherError(str(error)) from error
