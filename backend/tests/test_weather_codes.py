from app.infrastructure.open_meteo_client import WEATHER_CODES, _describe

# Códigos WMO que puede devolver Open-Meteo
WMO_CODES = {
    0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
    71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99,
}


def test_every_wmo_code_has_a_description():
    assert WMO_CODES <= WEATHER_CODES.keys()


def test_unknown_code_falls_back():
    assert _describe(1234) == "Sin datos"