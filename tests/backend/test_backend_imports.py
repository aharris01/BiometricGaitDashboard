def test_backend_imports():
    import backend

    backend


def test_app_instance():
    from backend.server.app import server

    assert server is not None
