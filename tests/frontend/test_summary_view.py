import pytest
from dash import html
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go

from frontend.views.summary_view import SummaryView


@pytest.mark.unit
def test_placeholder_figure_basic():
    view = SummaryView(
        event_id="evt-1", cmap=["#000000"], p100_data=None, grf_data=None
    )

    fig = view._placeholder_figure("Hello placeholder", height=300)

    assert isinstance(fig, go.Figure)
    # layout properties
    assert fig.layout.height == 300
    assert fig.layout.plot_bgcolor == "#e9f0fa"
    assert fig.layout.paper_bgcolor == "#e9f0fa"
    # annotation text
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Hello placeholder"


@pytest.mark.unit
def test_render_with_p100_and_grf():
    cmap = px.colors.sequential.Jet
    p100 = [[1, 2], [3, 4]]
    grf = [0.1, 0.2, 0.3]

    view = SummaryView(event_id="evt-123", cmap=cmap, p100_data=p100, grf_data=grf)
    root = view.render()

    # Root container
    assert isinstance(root, html.Div)
    assert len(root.children) == 2  # top_row, bottom_row

    top_row, bottom_row = root.children
    assert isinstance(top_row, html.Div)
    assert isinstance(bottom_row, html.Div)

    # ---- Top row: P100 + selected P100 ----
    # left: full P100
    p100_container = top_row.children[0]
    assert isinstance(p100_container, html.Div)
    assert isinstance(p100_container.children[0], html.H3)

    p100_graph = p100_container.children[1]
    assert isinstance(p100_graph, Graph)
    assert p100_graph.id == "p100-graph"
    assert isinstance(p100_graph.figure, go.Figure)

    # right: selected P100 (placeholder initially)
    selected_p100_container = top_row.children[1]
    assert isinstance(selected_p100_container, html.Div)
    assert isinstance(selected_p100_container.children[0], html.H4)

    selected_p100_graph = selected_p100_container.children[1]
    assert isinstance(selected_p100_graph, Graph)
    assert selected_p100_graph.id == "selected-p100-graph"
    assert isinstance(selected_p100_graph.figure, go.Figure)

    # ---- Bottom row: GRF + selected GRF ----
    grf_container = bottom_row.children[0]
    assert isinstance(grf_container, html.Div)
    assert isinstance(grf_container.children[0], html.H3)

    grf_graph = grf_container.children[1]
    assert isinstance(grf_graph, Graph)
    assert grf_graph.id == "grf-graph"
    assert isinstance(grf_graph.figure, go.Figure)

    selected_grf_container = bottom_row.children[1]
    assert isinstance(selected_grf_container, html.Div)
    assert isinstance(selected_grf_container.children[0], html.H4)

    selected_grf_graph = selected_grf_container.children[1]
    assert isinstance(selected_grf_graph, Graph)
    assert selected_grf_graph.id == "selected-grf-graph"
    assert isinstance(selected_grf_graph.figure, go.Figure)


@pytest.mark.unit
def test_render_without_p100_uses_placeholder():
    cmap = px.colors.sequential.Jet
    # No P100, but GRF available
    view = SummaryView(
        event_id="evt-no-p100", cmap=cmap, p100_data=None, grf_data=[1, 2, 3]
    )
    root = view.render()

    top_row = root.children[0]
    p100_container = top_row.children[0]
    p100_graph = p100_container.children[1]

    assert isinstance(p100_graph, Graph)
    assert p100_graph.id == "p100-graph"

    fig = p100_graph.figure
    assert isinstance(fig, go.Figure)
    # Placeholder text should match SummaryView implementation
    assert fig.layout.annotations[0].text == "P100 not available for this event."


@pytest.mark.unit
def test_render_without_grf_shows_text_placeholder():
    cmap = px.colors.sequential.Jet
    # P100 available, but no GRF data
    view = SummaryView(
        event_id="evt-no-grf", cmap=cmap, p100_data=[[1, 2], [3, 4]], grf_data=None
    )
    root = view.render()

    bottom_row = root.children[1]
    grf_container = bottom_row.children[0]

    # The left GRF area should be a Div with the "GRF not available" text
    left_grf = grf_container.children[1]
    assert isinstance(left_grf, html.Div)
    assert "GRF not available for this event." in left_grf.children

    # Selected GRF graph still exists and is a placeholder Graph
    selected_grf_container = bottom_row.children[1]
    selected_grf_graph = selected_grf_container.children[1]
    assert isinstance(selected_grf_graph, Graph)
    assert selected_grf_graph.id == "selected-grf-graph"
    assert isinstance(selected_grf_graph.figure, go.Figure)
