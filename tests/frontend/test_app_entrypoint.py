import pytest
from dash import Dash
from dash.html import Div

pytestmark = pytest.mark.unit


def test_frontend_app_import_smoke():
    # Import should not raise and should create a Dash instance and layout
    import frontend.app as appmod

    assert isinstance(appmod.app, Dash)
    assert isinstance(appmod.app.layout, Div)


def test_run_dash_does_not_start_server(monkeypatch):
    import frontend.app as appmod

    called = {
        "ok": False,
        "host": None,
        "port": None,
        "debug": None,
        "hot_reload": None,
    }

    def fake_run(*, host, port, debug, dev_tools_hot_reload):
        called["ok"] = True
        called["host"] = host
        called["port"] = port
        called["debug"] = debug
        called["hot_reload"] = dev_tools_hot_reload

    # Prevent a real server from starting
    monkeypatch.setattr(appmod.app, "run", fake_run)

    # Exercise run_dash()
    appmod.run_dash()

    assert called["ok"] is True
    assert called["hot_reload"] is False
    assert isinstance(called["host"], str)
    assert isinstance(called["port"], int)
