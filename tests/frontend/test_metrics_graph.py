import pytest
from dash import html
from frontend.views.metrics_graph import MetricsGraph


@pytest.mark.unit
def test_metrics_graph_renders_with_no_metrics():
    g = MetricsGraph({})
    out = g.render()
    assert isinstance(out, html.Div)


@pytest.mark.unit
def test_metrics_graph_renders_with_metrics():
    metrics = {
        "evt-1": {
            "avg_box_size": 10,
            "footstep_count": 3,
        }
    }
    g = MetricsGraph(metrics)
    out = g.render()
    assert isinstance(out, html.Div)
