# pyright: ignore[reportMissingImports]
"""Regresión: el exceso de rate limit debe devolver 429, no 500.

El before_request del limiter corre antes que el de logging; si g no está
inicializado, el after_request rompía con AttributeError y enmascaraba el 429.
"""


def test_rate_limit_returns_429_not_500(client):
    codes = set()
    for _ in range(125):
        codes.add(client.get("/api/v1/locations").status_code)
    assert codes == {200, 429}

    r = client.get("/api/v1/locations")
    assert r.status_code == 429
    assert r.get_json()["error"]
