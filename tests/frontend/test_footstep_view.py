import pytest
from dash import dcc, html

from frontend.api import API_BASE_URL
from frontend.views.footstep_view import (
    FootstepView,
    render_footstep_cards,
    render_footstep_empty,
)

pytestmark = pytest.mark.unit


def props(component):
    return component.to_plotly_json()["props"]


def children_list(component):
    children = props(component).get("children")
    if children is None:
        return []
    if isinstance(children, list):
        return children
    return [children]


def test_render_footstep_empty_returns_single_empty_div():
    out = render_footstep_empty("Nothing here")

    assert isinstance(out, list)
    assert len(out) == 1

    empty_div = out[0]
    assert isinstance(empty_div, html.Div)
    assert props(empty_div)["className"] == "footstep-empty"
    assert props(empty_div)["children"] == "Nothing here"


def test_render_footstep_cards_builds_titles_images_and_area_labels():
    items = [
        {
            "event_id": "evt-1",
            "footstep_id": 3,
            "step_number": 3,
            "bbox_area": 123,
            "has_thumbnail": True,
        },
        {
            "event_id": "evt-2",
            "footstep_id": 4,
            "step_number": 9,
            "bbox_area": None,
            "has_thumbnail": False,
        },
    ]

    cards = render_footstep_cards(items)

    assert len(cards) == 2

    first_children = children_list(cards[0])
    second_children = children_list(cards[1])

    assert isinstance(first_children[0], html.Div)
    assert props(first_children[0])["children"] == "evt-1 · Step 3"
    assert props(first_children[0])["className"] == "footstep-card-title"

    assert isinstance(first_children[1], html.Button)
    assert props(first_children[1])["className"] == "footstep-card-image-button"
    first_button_children = children_list(first_children[1])
    assert len(first_button_children) == 1
    assert isinstance(first_button_children[0], html.Img)
    assert (
        props(first_button_children[0])["src"]
        == f"{API_BASE_URL}/api/events/evt-1/footsteps/3/image?rev=0"
    )
    assert props(first_button_children[0])["className"] == "footstep-card-image"

    assert isinstance(first_children[2], html.Div)
    assert props(first_children[2])["children"] == "Area: 123"
    assert props(first_children[2])["className"] == "footstep-card-meta"

    assert isinstance(second_children[0], html.Div)
    assert props(second_children[0])["children"] == "evt-2 · Step 9"

    assert isinstance(second_children[1], html.Button)
    second_button_children = children_list(second_children[1])
    assert len(second_button_children) == 1
    assert isinstance(second_button_children[0], html.Div)
    assert props(second_button_children[0])["children"] == "Placeholder"
    assert props(second_button_children[0])["className"] == "footstep-card-placeholder"

    assert isinstance(second_children[2], html.Div)
    assert props(second_children[2])["children"] == "Area: N/A"


def test_footstep_view_renders_sidebar_filters_and_results_panel():
    root = FootstepView()

    assert isinstance(root, html.Div)
    assert props(root)["id"] == "footstep-view"
    assert props(root)["className"] == "hidden"

    root_children = children_list(root)
    assert len(root_children) == 4

    layout = root_children[0]
    history_modal = root_children[1]
    delete_modal = root_children[2]
    draft_modal = root_children[3]

    assert isinstance(layout, html.Div)
    assert props(layout)["className"] == "footstep-layout"

    assert isinstance(history_modal, html.Div)
    assert props(history_modal)["id"] == "footstep-history-modal"

    assert isinstance(delete_modal, html.Div)
    assert props(delete_modal)["id"] == "footstep-delete-modal"

    assert isinstance(draft_modal, html.Div)
    assert props(draft_modal)["id"] == "footstep-draft-modal"

    layout_children = children_list(layout)
    assert len(layout_children) == 2

    top_row = layout_children[0]
    bottom_row = layout_children[1]

    assert isinstance(top_row, html.Div)
    assert props(top_row)["className"] == "footstep-row footstep-top-row"

    assert isinstance(bottom_row, html.Div)
    assert props(bottom_row)["className"] == "footstep-row footstep-bottom-row"

    top_row_children = children_list(top_row)
    assert len(top_row_children) == 2

    sidebar = top_row_children[0]
    top_main = top_row_children[1]

    assert isinstance(sidebar, html.Div)
    assert props(sidebar)["className"] == "footstep-sidebar"

    assert isinstance(top_main, html.Div)
    assert props(top_main)["className"] == "footstep-top-main"

    top_main_children = children_list(top_main)
    assert len(top_main_children) == 1

    results_panel = top_main_children[0]

    assert isinstance(results_panel, html.Div)
    assert props(results_panel)["className"] == "footstep-results-panel"

    bottom_row_children = children_list(bottom_row)
    assert len(bottom_row_children) == 2

    context_panel = bottom_row_children[0]
    review_panel = bottom_row_children[1]

    assert isinstance(context_panel, html.Div)
    assert props(context_panel)["id"] == "footstep-context-panel"
    assert props(context_panel)["className"] == "footstep-context-panel"

    assert isinstance(review_panel, html.Div)
    assert props(review_panel)["id"] == "footstep-review-panel"
    assert props(review_panel)["className"] == "footstep-review-panel"

    # --------------------------------------------
    # Sidebar structure
    # --------------------------------------------
    sidebar_children = children_list(sidebar)
    assert len(sidebar_children) == 4

    header = sidebar_children[0]
    participant_details = sidebar_children[1]
    date_details = sidebar_children[2]
    size_details = sidebar_children[3]

    assert isinstance(header, html.Div)
    assert props(header)["className"] == "panel-header"

    header_children = children_list(header)
    assert len(header_children) == 2

    assert isinstance(header_children[0], html.H3)
    assert props(header_children[0])["children"] == "Filters"

    actions = header_children[1]
    assert isinstance(actions, html.Div)
    assert props(actions)["className"] == "footstep-filter-actions"

    actions_children = children_list(actions)
    assert len(actions_children) == 2

    assert isinstance(actions_children[0], html.Button)
    assert props(actions_children[0])["id"] == "btn-clear-footstep-filters"
    assert props(actions_children[0])["children"] == "Clear"

    assert isinstance(actions_children[1], html.Button)
    assert props(actions_children[1])["id"] == "btn-apply-footstep-filters"
    assert props(actions_children[1])["children"] == "OK"

    assert isinstance(participant_details, html.Details)
    assert props(participant_details)["open"] is False

    participant_children = children_list(participant_details)
    assert len(participant_children) == 2
    assert isinstance(participant_children[0], html.Summary)
    assert props(participant_children[0])["children"] == "by participant"

    participant_box = participant_children[1]
    assert isinstance(participant_box, html.Div)
    assert props(participant_box)["className"] == "filter_box"

    participant_box_children = children_list(participant_box)
    assert len(participant_box_children) == 1
    assert isinstance(participant_box_children[0], dcc.Checklist)
    assert props(participant_box_children[0])["id"] == "footstep-participant-filter"

    assert isinstance(date_details, html.Details)
    assert props(date_details)["open"] is False

    date_children = children_list(date_details)
    assert len(date_children) == 2
    assert isinstance(date_children[0], html.Summary)
    assert props(date_children[0])["children"] == "by date range"

    date_box = date_children[1]
    assert isinstance(date_box, html.Div)
    assert props(date_box)["className"] == "filter_box_no_scroll"

    date_box_children = children_list(date_box)
    assert len(date_box_children) == 1
    assert isinstance(date_box_children[0], dcc.DatePickerRange)
    assert props(date_box_children[0])["id"] == "footstep-date-range-filter"

    assert isinstance(size_details, html.Details)
    assert props(size_details)["open"] is False

    size_children = children_list(size_details)
    assert len(size_children) == 2
    assert isinstance(size_children[0], html.Summary)
    assert props(size_children[0])["children"] == "by footstep size"

    size_box = size_children[1]
    assert isinstance(size_box, html.Div)
    assert props(size_box)["className"] == "filter_box_no_scroll"

    size_box_children = children_list(size_box)
    assert len(size_box_children) == 3

    height_field = size_box_children[0]
    width_field = size_box_children[1]
    total_field = size_box_children[2]

    height_children = children_list(height_field)
    assert props(height_children[0])["children"] == "Height"
    assert isinstance(height_children[1], dcc.RangeSlider)
    assert props(height_children[1])["id"] == "footstep-height-slider"
    assert props(height_children[1])["value"] == [10, 150]

    width_children = children_list(width_field)
    assert props(width_children[0])["children"] == "Width"
    assert isinstance(width_children[1], dcc.RangeSlider)
    assert props(width_children[1])["id"] == "footstep-width-slider"
    assert props(width_children[1])["value"] == [10, 130]

    total_children = children_list(total_field)
    assert props(total_children[0])["children"] == "Total Footstep Size"
    assert isinstance(total_children[1], dcc.RangeSlider)
    assert props(total_children[1])["id"] == "footstep-size-slider"
    assert props(total_children[1])["value"] == [0, 10000]

    # --------------------------------------------
    # Results panel
    # --------------------------------------------
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
        == "Choose filters, then press OK."
    )

    assert isinstance(results_grid, html.Div)
    assert props(results_grid)["id"] == "footstep-results-grid"
    default_children = children_list(results_grid)
    assert len(default_children) == 1
    assert isinstance(default_children[0], html.Div)
    assert props(default_children[0])["className"] == "footstep-empty"
    assert (
        props(default_children[0])["children"]
        == "No footsteps loaded yet. Choose filters and press OK."
    )

    assert isinstance(load_more_wrap, html.Div)
    assert props(load_more_wrap)["id"] == "footstep-load-more-wrap"
    assert props(load_more_wrap)["style"] == {"display": "none", "marginTop": "12px"}

    load_more_children = children_list(load_more_wrap)
    assert len(load_more_children) == 1
    assert isinstance(load_more_children[0], html.Button)
    assert props(load_more_children[0])["id"] == "btn-load-more-footsteps"
    assert props(load_more_children[0])["children"] == "Load More"

    # --------------------------------------------
    # Context panel
    # --------------------------------------------
    context_children = children_list(context_panel)
    assert len(context_children) == 4

    context_header = context_children[0]
    context_meta = context_children[1]
    context_p100 = context_children[2]
    context_grf = context_children[3]

    assert isinstance(context_header, html.Div)
    context_header_children = children_list(context_header)
    assert isinstance(context_header_children[0], html.H3)
    assert props(context_header_children[0])["id"] == "footstep-context-title"
    assert props(context_header_children[0])["children"] == "Footstep Context"

    assert isinstance(context_meta, html.Div)
    assert props(context_meta)["id"] == "footstep-context-meta"
    assert (
        props(context_meta)["children"] == "Click a thumbnail to inspect that footstep."
    )

    assert isinstance(context_p100, dcc.Graph)
    assert props(context_p100)["id"] == "footstep-context-p100-graph"

    assert isinstance(context_grf, dcc.Graph)
    assert props(context_grf)["id"] == "footstep-context-grf-graph"

    # --------------------------------------------
    # Draft modal
    # --------------------------------------------
    draft_children = children_list(draft_modal)
    assert len(draft_children) == 1
    assert isinstance(draft_children[0], html.Div)
