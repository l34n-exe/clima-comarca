import time

import requests # type: ignore
from flask import current_app # type: ignore

from ..core.exceptions import WeatherError


def _retryable(exc):
    # 4xx es culpa del pedido: reintentar no cambia nada. 429 tampoco: el
    # proveedor está limitando y reintentar rápido empeora el bloqueo, así
    # que falla directo y el servicio pasa al respaldo. Solo 5xx y fallos
    # de red/conexión pueden ser transitorios.
    if not isinstance(exc, requests.HTTPError):
        return True
    status = exc.response.status_code if exc.response is not None else 0
    return status >= 500


def get(url, params=None, headers=None):
    """GET con timeout, reintentos y backoff exponencial ante fallos transitorios."""
    timeout = current_app.config["HTTP_TIMEOUT"]
    retries = current_app.config["HTTP_RETRIES"]
    backoff = current_app.config["HTTP_RETRY_BACKOFF"]
    error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            error = exc
            if not _retryable(exc):
                break
            # Algunos 5xx (por ejemplo 503) traen Retry-After: se respeta
            # con un tope para no demorar el respaldo más de la cuenta
            wait = backoff * (2**attempt)
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                response_headers = getattr(exc.response, "headers", None) or {}
                retry_after = response_headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = max(wait, min(int(retry_after), 10))
            if attempt < retries - 1:
                time.sleep(wait)
            continue
    current_app.logger.warning("Proveedor inaccesible tras %s intentos: %s %s", retries, url, error)
    raise WeatherError(str(error)) from error
