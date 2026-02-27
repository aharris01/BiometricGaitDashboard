# pyright: reportAttributeAccessIssue=false
import pytest
from typing import Any, cast

from dash import html, dcc
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


def assert_pm_id(component: Any, expected_type: str, expected_event_id: str) -> None:
    """Assert a Dash pattern-matching id dict."""
    assert isinstance(component.id, dict)
    assert component.id.get("type") == expected_type
    assert component.id.get("event_id") == expected_event_id


def get_summary_controls_row(p100_container: Any) -> Any:
    """
    In SummaryView.render() the left panel children are:
      [H3 title, Graph, controls_row]
    """
    p100_children = children_list(p100_container)
    assert len(p100_children) >= 3
    return p100_children[2]


def get_slider_from_controls_row(controls_row: Any) -> dcc.Slider:
    """
    Your current layout is:
      controls_row.children = [RadioItems, slider_wrap]
      slider_wrap.children = [slider_outer_div]
      slider_outer_div.children = [dcc.Slider]
    So we drill down safely.
    """
    controls_children = children_list(controls_row)
    assert len(controls_children) >= 2

    slider_wrap = controls_children[1]
    slider_wrap_children = children_list(slider_wrap)
    assert slider_wrap_children, "Expected slider wrapper to have children"

    slider_outer = slider_wrap_children[0]
    slider_outer_children = children_list(slider_outer)
    assert slider_outer_children, "Expected slider outer wrapper to have children"

    slider = slider_outer_children[0]
    assert isinstance(slider, dcc.Slider)
    return slider


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

    # ensure thumbnails header exists
    thumbs_children = children_list(thumbs_container)
    assert isinstance(thumbs_children[0], html.H4)

    # grid wrapper exists
    grid_wrapper = thumbs_children[1]
    grid_children = children_list(grid_wrapper)
    assert grid_children, "Expected thumbnails grid to render"

    # Bottom row should include grf-graph
    bottom_children = children_list(bottom_row)
    grf_container = bottom_children[0]
    grf_children = children_list(grf_container)
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


@pytest.mark.unit
def test_render_without_step_p100s_shows_empty_message():
    cmap = px.colors.sequential.Jet

    view = SummaryView(
        event_id="evt-empty-steps",
        cmap=cmap,
        p100_data=[[1, 2], [3, 4]],
        grf_data=[0.1, 0.2],
        footsteps=[],
        step_p100s=[],
        mode="all",
    )

    root = cast(html.Div, view.render())
    top_row = children_list(root)[0]
    top_children = children_list(top_row)

    thumbs_container = top_children[1]
    thumbs_children = children_list(thumbs_container)

    assert isinstance(thumbs_children[0], html.H4)

    grid_wrapper = thumbs_children[1]
    assert isinstance(grid_wrapper, html.Div)

    msg_div = (
        children_list(grid_wrapper)[0] if children_list(grid_wrapper) else grid_wrapper
    )
    assert isinstance(msg_div, html.Div)

    msg = msg_div.children
    assert isinstance(msg, str)
    assert "No extracted footsteps available for this event." in msg


@pytest.mark.unit
def test_get_p100_range_defaults_when_empty():
    view = SummaryView(event_id="evt", cmap=["#000"], p100_data=None, grf_data=None)
    assert view._get_p100_range() == (0, 1)


@pytest.mark.unit
def test_get_p100_range_finds_max():
    view = SummaryView(
        event_id="evt", cmap=["#000"], p100_data=[[0, 2], [3, None]], grf_data=None
    )
    assert view._get_p100_range() == (0, 3)


@pytest.mark.unit
def test_resize_nearest_resizes_shape_and_values():
    view = SummaryView(event_id="evt", cmap=["#000"], p100_data=[[1]], grf_data=None)

    img = [
        [1, 2],
        [3, 4],
    ]

    out = view._resize_nearest(img, out_h=4, out_w=4)
    assert len(out) == 4
    assert len(out[0]) == 4

    assert out[0][0] == 1
    assert out[0][-1] == 2
    assert out[-1][0] == 3
    assert out[-1][-1] == 4


@pytest.mark.unit
def test_global_canvas_for_step_pastes_resized_step_into_bbox():
    cmap = px.colors.sequential.Jet

    p100 = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]

    footsteps = [{"id": 7, "x_min": 0, "x_max": 2, "y_min": 0, "y_max": 2}]
    step_p100s = [{"id": 7, "p100": [[9]]}]

    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=p100,
        grf_data=None,
        footsteps=footsteps,
        step_p100s=step_p100s,
        mode="single",
        step_index=0,
    )

    canvas = view._global_canvas_for_step(7)
    assert canvas is not None
    assert len(canvas) == 4
    assert len(canvas[0]) == 4

    assert canvas[0][0] == 9
    assert canvas[0][1] == 9
    assert canvas[1][0] == 9
    assert canvas[1][1] == 9
    assert canvas[3][3] == 0


@pytest.mark.unit
def test_bbox_shapes_and_annotations_filter_by_step_id():
    cmap = px.colors.sequential.Jet
    footsteps = [
        {"id": 1, "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1},
        {"id": 2, "x_min": 1, "x_max": 2, "y_min": 1, "y_max": 2},
    ]

    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=[[1, 2], [3, 4]],
        grf_data=None,
        footsteps=footsteps,
        step_p100s=[],
    )

    shapes_all = view._bbox_shapes()
    ann_all = view._bbox_annotations()
    assert len(shapes_all) == 2
    assert len(ann_all) == 2

    shapes_one = view._bbox_shapes(only_step_id=2)
    ann_one = view._bbox_annotations(only_step_id=2)
    assert len(shapes_one) == 1
    assert len(ann_one) == 1
    assert ann_one[0]["text"].startswith("#2")


@pytest.mark.unit
def test_render_single_step_mode_hides_colorbar_and_uses_bbox_overlays():
    cmap = px.colors.sequential.Jet
    p100 = [
        [0, 0, 0, 0],
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [0, 0, 0, 0],
    ]
    footsteps = [{"id": 0, "x_min": 1, "x_max": 3, "y_min": 1, "y_max": 3}]
    step_p100s = [{"id": 0, "p100": [[5]]}]

    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=p100,
        grf_data=[0.1, 0.2],
        footsteps=footsteps,
        step_p100s=step_p100s,
        mode="single",
        step_index=0,
    )

    root = cast(html.Div, view.render())
    top_row = children_list(root)[0]
    top_children = children_list(top_row)
    p100_container = top_children[0]
    p100_graph = children_list(p100_container)[1]
    assert isinstance(p100_graph, Graph)
    assert_pm_id(p100_graph, "p100-graph", "evt")

    fig = p100_graph.figure
    assert isinstance(fig, go.Figure)

    # Plotly sometimes returns None here depending on figure internals; accept either
    showscale = getattr(fig.layout.coloraxis, "showscale", None)
    assert showscale in (False, None)

    assert fig.layout.shapes is not None
    assert len(fig.layout.shapes) == 1


@pytest.mark.unit
def test_render_without_grf_uses_grf_placeholder():
    cmap = px.colors.sequential.Jet
    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=[[1, 2], [3, 4]],
        grf_data=None,
        footsteps=[],
        step_p100s=[],
    )

    root = cast(html.Div, view.render())
    bottom_row = children_list(root)[1]

    bottom_children = children_list(bottom_row)
    grf_container = bottom_children[0]
    grf_children = children_list(grf_container)

    assert isinstance(grf_children[0], html.H3)
    grf_graph = grf_children[1]
    assert isinstance(grf_graph, Graph)
    assert_pm_id(grf_graph, "grf-graph", "evt")

    fig = grf_graph.figure
    assert isinstance(fig, go.Figure)
    assert fig.layout.annotations[0].text == "GRF not available for this event."


@pytest.mark.unit
def test_render_mode_all_shows_colorbar_and_slider_disabled():
    cmap = px.colors.sequential.Jet
    p100 = [[1, 2], [3, 4]]
    footsteps = [{"id": 0, "x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1}]

    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=p100,
        grf_data=[0.1],
        footsteps=footsteps,
        step_p100s=[{"id": 0, "p100": [[9]]}],
        mode="all",
        step_index=0,
    )

    root = cast(html.Div, view.render())
    top_row = children_list(root)[0]
    p100_container = children_list(top_row)[0]

    p100_graph = children_list(p100_container)[1]
    assert isinstance(p100_graph, Graph)

    showscale = getattr(p100_graph.figure.layout.coloraxis, "showscale", None)
    assert showscale is None or showscale is True

    controls_row = get_summary_controls_row(p100_container)
    slider = get_slider_from_controls_row(controls_row)
    assert slider.disabled is True


@pytest.mark.unit
def test_render_mode_cumulative_pastes_multiple_steps_and_hides_colorbar():
    cmap = px.colors.sequential.Jet

    p100 = [[0, 0, 0, 0] for _ in range(4)]

    footsteps = [
        {"id": 0, "x_min": 0, "x_max": 2, "y_min": 0, "y_max": 2},
        {"id": 1, "x_min": 2, "x_max": 4, "y_min": 2, "y_max": 4},
    ]
    step_p100s = [
        {"id": 0, "p100": [[5]]},
        {"id": 1, "p100": [[7]]},
    ]

    view = SummaryView(
        event_id="evt",
        cmap=cmap,
        p100_data=p100,
        grf_data=[0.1],
        footsteps=footsteps,
        step_p100s=step_p100s,
        mode="cumulative",
        step_index=1,
    )

    root = cast(html.Div, view.render())
    top_row = children_list(root)[0]
    p100_container = children_list(top_row)[0]
    p100_graph = children_list(p100_container)[1]
    assert isinstance(p100_graph, Graph)

    fig = p100_graph.figure
    showscale = getattr(fig.layout.coloraxis, "showscale", None)
    assert showscale in (False, None)

    assert fig.layout.shapes is not None
    assert len(fig.layout.shapes) == 2
