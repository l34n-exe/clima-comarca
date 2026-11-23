from app.services import cache_service


def test_lock_is_exclusive_and_released_by_owner(app):
    with app.app_context():
        token = cache_service.acquire_lock("k", 30)
        assert token
        # Otro proceso no puede tomar el mismo candado
        assert cache_service.acquire_lock("k", 30) is None
        # Un token ajeno no libera el candado
        cache_service.release_lock("k", "token-ajeno")
        assert cache_service.acquire_lock("k", 30) is None
        # El dueño sí lo libera
        cache_service.release_lock("k", token)
        assert cache_service.acquire_lock("k", 30)


def test_lock_expires_by_itself(app):
    with app.app_context():
        cache_service.acquire_lock("k2", 1)
        import time

        time.sleep(1.1)
        assert cache_service.acquire_lock("k2", 30)
