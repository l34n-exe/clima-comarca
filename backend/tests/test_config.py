import pytest

from tests.conftest import make_app


def test_cors_origins_are_trimmed():
    app = make_app(CORS_ORIGINS="https://web.example, http://localhost:5173 ")
    assert app.config["CORS_ORIGINS"] == [
        "https://web.example",
        "http://localhost:5173",
    ]


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("CACHE_TTL_CURRENT", -1, "no puede ser negativo"),
        ("CACHE_TTL_FORECAST", "1.5", "debe ser un número entero"),
        ("HTTP_TIMEOUT", 0, "debe ser mayor que cero"),
        ("CORS_ORIGINS", ["https://ok.example", None], "debe ser texto"),
    ],
)
def test_invalid_config_fails_at_app_creation(setting, value, message):
    with pytest.raises(ValueError, match=message):
        make_app(**{setting: value})
