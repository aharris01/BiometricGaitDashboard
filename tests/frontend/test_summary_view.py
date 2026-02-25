# pyright: reportAttributeAccessIssue=false
import pytest
from typing import Any, cast

from dash import html
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go

from frontend.views.swipe_event_view.summary_view import SummaryView


def children_list(component: Any) -> list[Any]:
    children = getattr(component, "children", None)
    if children is None:
        return []
    if isinstance(children, list):
        return list(children)
    return [children]


@pytest.mark.unit
def test_placeholder_figure_basic():
    view = SummaryView(
        event_id="evt-1", cmap=["#000000"], p100_data=None, grf_data=None
    )
    fig = view._placeholder_figure("Hello placeholder", height=300)
    assert isinstance(fig, go.Figure)
    assert fig.layout.height == 300
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Hello placeholder"


@pytest.mark.unit
def test_render_with_p100_and_grf_and_thumbnails():
    cmap = px.colors.sequential.Jet
    p100 = [[1, 2], [3, 4]]
    grf = [0.1, 0.2, 0.3]
    footsteps = [{"id": 0, "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1}]
    step_p100s = [{"id": 0, "p100": [[1, 0], [0, 1]], "grf": [0.5, 0.6]}]

    view = SummaryView(
        event_id="evt-123",
        cmap=cmap,
        p100_data=p100,
        grf_data=grf,
        footsteps=footsteps,
        step_p100s=step_p100s,
    )
    root = cast(html.Div, view.render())
    assert isinstance(root, html.Div)

    root_children = children_list(root)
    assert len(root_children) == 2

    top_row = root_children[0]
    bottom_row = root_children[1]
    assert isinstance(top_row, html.Div)
    assert isinstance(bottom_row, html.Div)

    # Top row has two columns: left p100, right thumbnails
    top_children = children_list(top_row)
    assert len(top_children) == 2

    p100_container = top_children[0]
    thumbs_container = top_children[1]

    p100_children = children_list(p100_container)
    p100_graph = p100_children[1]
    assert isinstance(p100_graph, Graph)
    assert p100_graph.id == {"type": "p100-graph", "event_id": "evt-123"}

    # ensure at least one thumbnail graph exists
    thumbs_children = children_list(thumbs_container)
    assert isinstance(thumbs_children[0], html.H4)

    # the second child is a Div that contains the grid
    grid_wrapper = thumbs_children[1]
    grid_children = children_list(grid_wrapper)
    # grid_wrapper children is either text Div or grid Div; with step_p100s it should be grid
    assert grid_children, "Expected thumbnails grid to render"

    # Bottom row should include grf-graph
    bottom_children = children_list(bottom_row)
    grf_container = bottom_children[0]
    grf_children = children_list(grf_container)
    # title then graph
    assert isinstance(grf_children[0], html.H3)
    assert isinstance(grf_children[1], Graph)
    assert grf_children[1].id == {"type": "grf-graph", "event_id": "evt-123"}


@pytest.mark.unit
def test_render_without_p100_uses_placeholder():
    cmap = px.colors.sequential.Jet
    view = SummaryView(
        event_id="evt-no-p100", cmap=cmap, p100_data=None, grf_data=[1, 2, 3]
    )
    root = cast(html.Div, view.render())

    top_row = children_list(root)[0]
    top_children = children_list(top_row)
    p100_container = top_children[0]
    p100_graph = children_list(p100_container)[1]
    assert isinstance(p100_graph, Graph)
    assert p100_graph.id == {"type": "p100-graph", "event_id": "evt-no-p100"}
    fig = p100_graph.figure
    assert isinstance(fig, go.Figure)
    assert fig.layout.annotations[0].text == "P100 not available for this event."
