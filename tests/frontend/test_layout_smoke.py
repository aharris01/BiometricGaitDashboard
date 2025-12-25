import pytest
from dash.html import Div
from frontend.layout import build_layout

@pytest.mark.unit
def test_build_layout_returns_div():
    layout = build_layout()
    assert isinstance(layout, Div)
