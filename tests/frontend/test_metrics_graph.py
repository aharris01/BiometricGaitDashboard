import pytest
from dash import html
from frontend.views.metrics_graph import MetricsGraph


@pytest.mark.unit
def test_metrics_graph_renders_with_no_footsteps():
    g = MetricsGraph("evt-1", footsteps=[])
    out = g.render()
    assert isinstance(out, html.Div)


@pytest.mark.unit
def test_metrics_graph_renders_with_footsteps():
    footsteps = [{"x_min": 0, "x_max": 10, "y_min": 0, "y_max": 10}]
    g = MetricsGraph("evt-1", footsteps=footsteps)
    out = g.render()
    assert isinstance(out, html.Div)


def test_metrics_graph_placeholder_branch():
    from frontend.views.metrics_graph import MetricsGraph

    g = MetricsGraph(metrics={})
    out = g.render()
    assert out is not None
