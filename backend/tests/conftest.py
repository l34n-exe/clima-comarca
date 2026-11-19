import fakeredis
import pytest

from app import create_app


def make_app(**extra):
    config = {"TESTING": True, "REDIS_CLIENT": fakeredis.FakeRedis(decode_responses=True)}
    config.update(extra)
    return create_app(config)


@pytest.fixture
def app():
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()
