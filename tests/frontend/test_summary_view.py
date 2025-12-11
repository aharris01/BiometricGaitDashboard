# pyright: reportAttributeAccessIssue=false

import pytest
from typing import Any, cast

from dash import html
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go

from frontend.views.summary_view import SummaryView


def children_list(component: Any) -> list[Any]:
    """
    Dash components can have children = None | single child | list[child].
    This helper always returns a list so the type checker is happy.
    """
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
    assert fig.layout.plot_bgcolor == "#e9f0fa"
    assert fig.layout.paper_bgcolor == "#e9f0fa"
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Hello placeholder"


@pytest.mark.unit
def test_render_with_p100_and_grf_and_dotplot():
    cmap = px.colors.sequential.Jet
    p100 = [[1, 2], [3, 4]]
    grf = [0.1, 0.2, 0.3]

    view = SummaryView(event_id="evt-123", cmap=cmap, p100_data=p100, grf_data=grf)
    root = cast(html.Div, view.render())

    assert isinstance(root, html.Div)
    root_children = children_list(root)
    assert len(root_children) == 3

    top_row = root_children[0]
    bottom_row = root_children[1]
    above_top_row = root_children[2]
    assert isinstance(top_row, html.Div)
    assert isinstance(bottom_row, html.Div)
    assert isinstance(above_top_row, html.Div)

    # ---- Top row ----
    top_children = children_list(top_row)
    p100_container = top_children[0]
    selected_p100_container = top_children[1]

    p100_children = children_list(p100_container)
    assert isinstance(p100_children[0], html.H3)

    p100_graph_any: Any = p100_children[1]
    assert isinstance(p100_graph_any, Graph)
    assert p100_graph_any.id == "p100-graph"
    assert isinstance(p100_graph_any.figure, go.Figure)

    selected_p100_children = children_list(selected_p100_container)
    assert isinstance(selected_p100_children[0], html.H4)

    selected_p100_graph_any: Any = selected_p100_children[1]
    assert isinstance(selected_p100_graph_any, Graph)
    assert selected_p100_graph_any.id == "selected-p100-graph"
    assert isinstance(selected_p100_graph_any.figure, go.Figure)

    # ---- Bottom row ----
    bottom_children = children_list(bottom_row)
    grf_container = bottom_children[0]
    selected_grf_container = bottom_children[1]

    grf_children = children_list(grf_container)
    assert isinstance(grf_children[0], html.H3)

    grf_graph_any: Any = grf_children[1]
    assert isinstance(grf_graph_any, Graph)
    assert grf_graph_any.id == "grf-graph"
    assert isinstance(grf_graph_any.figure, go.Figure)

    selected_grf_children = children_list(selected_grf_container)
    assert isinstance(selected_grf_children[0], html.H4)

    selected_grf_graph_any: Any = selected_grf_children[1]
    assert isinstance(selected_grf_graph_any, Graph)
    assert selected_grf_graph_any.id == "selected-grf-graph"
    assert isinstance(selected_grf_graph_any.figure, go.Figure)

    # ---- Above top row ----
    above_top_children = children_list(above_top_row)
    dotplot_container = above_top_children[0]

    dotplot_children = children_list(dotplot_container)
    assert isinstance(dotplot_children[0], html.H3)

    dotplot_graph_any: Any = dotplot_children[1]
    assert isinstance(dotplot_graph_any, Graph)
    assert dotplot_graph_any.id == "dotplot"
    assert isinstance(dotplot_graph_any.figure, go.Figure)



@pytest.mark.unit
def test_render_without_p100_uses_placeholder():
    cmap = px.colors.sequential.Jet
    view = SummaryView(
        event_id="evt-no-p100",
        cmap=cmap,
        p100_data=None,
        grf_data=[1, 2, 3],
    )
    root = cast(html.Div, view.render())

    root_children = children_list(root)
    top_row = root_children[0]
    top_children = children_list(top_row)
    p100_container = top_children[0]
    p100_children = children_list(p100_container)

    p100_graph_any: Any = p100_children[1]
    assert isinstance(p100_graph_any, Graph)
    assert p100_graph_any.id == "p100-graph"

    fig = p100_graph_any.figure
    assert isinstance(fig, go.Figure)
    assert fig.layout.annotations[0].text == "P100 not available for this event."


@pytest.mark.unit
def test_render_without_grf_shows_text_placeholder():
    cmap = px.colors.sequential.Jet
    view = SummaryView(
        event_id="evt-no-grf",
        cmap=cmap,
        p100_data=[[1, 2], [3, 4]],
        grf_data=None,
    )
    root = cast(html.Div, view.render())

    root_children = children_list(root)
    bottom_row = root_children[1]
    bottom_children = children_list(bottom_row)
    grf_container = bottom_children[0]

    grf_children = children_list(grf_container)
    left_grf = grf_children[1]

    assert isinstance(left_grf, html.Div)
    left_children = children_list(left_grf)
    text_content = " ".join(str(c) for c in left_children) if left_children else ""
    assert "GRF not available for this event." in text_content

    selected_grf_container = bottom_children[1]
    selected_grf_children = children_list(selected_grf_container)
    selected_grf_graph_any: Any = selected_grf_children[1]

    assert isinstance(selected_grf_graph_any, Graph)
    assert selected_grf_graph_any.id == "selected-grf-graph"
    assert isinstance(selected_grf_graph_any.figure, go.Figure)
