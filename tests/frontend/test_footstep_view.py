import pytest
from dash import dcc, html

from frontend.api import API_BASE_URL
from frontend.views.footstep_view import (
    FootstepView,
    render_footstep_cards,
    render_footstep_empty,
)


def props(component):
    return component.to_plotly_json()["props"]


def children_list(component):
    children = props(component).get("children")
    if children is None:
        return []
    if isinstance(children, list):
        return children
    return [children]


@pytest.mark.unit
def test_render_footstep_empty_returns_single_empty_div():
    out = render_footstep_empty("Nothing here")

    assert isinstance(out, list)
    assert len(out) == 1

    empty_div = out[0]
    assert isinstance(empty_div, html.Div)
    assert props(empty_div)["className"] == "footstep-empty"
    assert props(empty_div)["children"] == "Nothing here"


@pytest.mark.unit
def test_render_footstep_cards_builds_titles_images_and_area_labels():
    items = [
        {"event_id": "evt-1", "footstep_id": 3, "bbox_area": 123},
        {"event_id": "evt-2", "footstep_id": 4, "bbox_area": None},
    ]

    cards = render_footstep_cards(items)

    assert len(cards) == 2

    first_children = children_list(cards[0])
    second_children = children_list(cards[1])

    assert isinstance(first_children[0], html.Div)
    assert props(first_children[0])["children"] == "evt-1 · Step 3"
    assert props(first_children[0])["className"] == "footstep-card-title"

    assert isinstance(first_children[1], html.Img)
    assert (
        props(first_children[1])["src"]
        == f"{API_BASE_URL}/api/events/evt-1/footsteps/3/image"
    )
    assert props(first_children[1])["className"] == "footstep-card-image"

    assert isinstance(first_children[2], html.Div)
    assert props(first_children[2])["children"] == "Area: 123"
    assert props(first_children[2])["className"] == "footstep-card-meta"

    assert isinstance(second_children[0], html.Div)
    assert props(second_children[0])["children"] == "evt-2 · Step 4"

    assert isinstance(second_children[1], html.Img)
    assert (
        props(second_children[1])["src"]
        == f"{API_BASE_URL}/api/events/evt-2/footsteps/4/image"
    )

    assert isinstance(second_children[2], html.Div)
    assert props(second_children[2])["children"] == "Area: N/A"


@pytest.mark.unit
def test_footstep_view_renders_expected_controls_and_default_state():
    root = FootstepView()

    assert isinstance(root, html.Div)
    assert props(root)["id"] == "footstep-view"
    assert props(root)["className"] == "hidden"

    root_children = children_list(root)
    assert len(root_children) == 1

    row = root_children[0]
    assert isinstance(row, html.Div)
    assert props(row)["className"] == "footstep-row"

    row_children = children_list(row)
    assert len(row_children) == 2

    sidebar = row_children[0]
    results_panel = row_children[1]

    assert isinstance(sidebar, html.Div)
    assert props(sidebar)["className"] == "footstep-sidebar"

    assert isinstance(results_panel, html.Div)
    assert props(results_panel)["className"] == "footstep-results-panel"

    sidebar_children = children_list(sidebar)
    assert len(sidebar_children) == 3

    header = sidebar_children[0]
    field = sidebar_children[1]
    apply_button = sidebar_children[2]

    assert isinstance(header, html.Div)
    assert isinstance(children_list(header)[0], html.H3)
    assert props(children_list(header)[0])["children"] == "Filters"

    assert isinstance(field, html.Div)
    field_children = children_list(field)
    assert isinstance(field_children[0], html.Label)
    assert props(field_children[0])["children"] == "Bounding Box Area"
    assert isinstance(field_children[1], dcc.RangeSlider)
    assert props(field_children[1])["id"] == "footstep-size-slider"
    assert props(field_children[1])["value"] == [0, 30000]

    assert isinstance(apply_button, html.Button)
    assert props(apply_button)["id"] == "btn-apply-footstep-filters"
    assert props(apply_button)["children"] == "Apply"

    results_children = children_list(results_panel)
    assert len(results_children) == 3

    results_header = results_children[0]
    results_grid = results_children[1]
    load_more_wrap = results_children[2]

    assert isinstance(results_header, html.Div)
    results_header_children = children_list(results_header)
    assert isinstance(results_header_children[0], html.H3)
    assert props(results_header_children[0])["children"] == "Footsteps"
    assert isinstance(results_header_children[1], html.Div)
    assert props(results_header_children[1])["id"] == "footstep-results-status"
    assert (
        props(results_header_children[1])["children"]
        == "Choose filters, then press Apply."
    )

    assert isinstance(results_grid, html.Div)
    assert props(results_grid)["id"] == "footstep-results-grid"
    default_children = children_list(results_grid)
    assert len(default_children) == 1
    assert isinstance(default_children[0], html.Div)
    assert props(default_children[0])["className"] == "footstep-empty"
    assert (
        props(default_children[0])["children"]
        == "No footsteps loaded yet. Choose a size range and press Apply."
    )

    assert isinstance(load_more_wrap, html.Div)
    assert props(load_more_wrap)["id"] == "footstep-load-more-wrap"
    assert props(load_more_wrap)["style"] == {"display": "none", "marginTop": "12px"}

    load_more_children = children_list(load_more_wrap)
    assert len(load_more_children) == 1
    assert isinstance(load_more_children[0], html.Button)
    assert props(load_more_children[0])["id"] == "btn-load-more-footsteps"
    assert props(load_more_children[0])["children"] == "Load More"
