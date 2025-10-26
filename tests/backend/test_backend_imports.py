def test_backend_imports():
    import backend


def test_app_instance():
    from backend.app import server

    assert server is not None
