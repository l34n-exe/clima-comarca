def test_list_all(client):
    data = client.get("/api/v1/locations").get_json()
    assert len(data) >= 2


def test_search_ignores_accents(client):
    data = client.get("/api/v1/locations?q=condor").get_json()
    assert [loc["slug"] for loc in data] == ["el-condor"]


def test_new_coastal_locations_are_available_and_searchable_without_accents(client):
    locations = client.get("/api/v1/locations").get_json()
    by_slug = {location["slug"]: location for location in locations}
    expected = {
        "bahia-rosas": "Bahía Rosas",
        "bajada-de-echandi": "Bajada de Echandi",
        "playa-winter": "Playa Winter",
        "pozo-salado": "Pozo Salado",
        "bahia-san-blas": "Bahía San Blas",
    }

    for slug, name in expected.items():
        assert by_slug[slug]["nombre"] == name
        assert by_slug[slug]["tipo"] == "playa"

    matches = client.get("/api/v1/locations?q=bahia").get_json()
    assert {location["slug"] for location in matches} == {
        "bahia-creek",
        "bahia-rosas",
        "bahia-san-blas",
    }


def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.get_json()["redis"] is True
