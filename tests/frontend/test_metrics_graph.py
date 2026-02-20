import pytest
from dash import html
from frontend.views.metrics_graph import MetricsGraph
import plotly.graph_objects as go


@pytest.mark.unit
def test_metrics_graph_renders_with_no_metrics():
    # Graph should render a container even if no metrics are provided
    g = MetricsGraph({})
    out = g.render()
    assert isinstance(out, html.Div)


@pytest.mark.unit
def test_metrics_graph_renders_with_metrics():
    # Graph should still render normally when metrics exist
    metrics = {
        "evt-1": {
            "avg_box_size": 10,
            "footstep_count": 3,
        }
    }
    g = MetricsGraph(metrics)
    out = g.render()
    assert isinstance(out, html.Div)


@pytest.mark.unit
def test_build_scatter_no_metrics_returns_placeholder():
    # When no metrics are available, a placeholder figure should be returned
    g = MetricsGraph({})
    fig = g._build_scatter("avg_box_size", "footstep_count")

    assert isinstance(fig, go.Figure)
    # Verify annotation text test
    layout_dict = fig.to_dict()["layout"]
    annotations = layout_dict.get("annotations", [])
    assert any("no metrics data" in a.get("text", "").lower() for a in annotations)


@pytest.mark.unit
def test_build_scatter_missing_values_returns_placeholder():
    # When metric values are missing (None), no valid points should be plotted
    metrics = {
        "evt-1": {"avg_box_size": None, "footstep_count": 3},
        "evt-2": {"avg_box_size": 5, "footstep_count": None},
    }
    g = MetricsGraph(metrics)
    fig = g._build_scatter("avg_box_size", "footstep_count")
    # Verify placeholder annotation for missing values
    layout_dict = fig.to_dict()["layout"]
    annotations = layout_dict.get("annotations", [])
    assert any("missing values" in a.get("text", "").lower() for a in annotations)


@pytest.mark.unit
def test_build_scatter_valid_points():
    # When valid numeric metrics are present, a scatter trace should be built
    metrics = {
        "evt-1": {"avg_box_size": 10, "footstep_count": 3},
        "evt-2": {"avg_box_size": 20, "footstep_count": 5},
    }
    g = MetricsGraph(metrics)
    fig = g._build_scatter("avg_box_size", "footstep_count")

    fig_dict = fig.to_dict()

    # Ensure exactly one scatter trace was created
    assert len(fig_dict["data"]) == 1

    trace = fig_dict["data"][0]
    # Validate plotted X and Y values and associated event IDs
    assert trace["x"] == [10.0, 20.0]
    assert trace["y"] == [3.0, 5.0]
    assert trace["text"] == ["evt-1", "evt-2"]
    # Validate axis labels are correctly mapped
    assert fig_dict["layout"]["xaxis"]["title"]["text"] == "Average Bounding Box Size"
    assert fig_dict["layout"]["yaxis"]["title"]["text"] == "Footstep Count"
