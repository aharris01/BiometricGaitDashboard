# frontend/layout.py
from dash.dcc import Interval, Store, ConfirmDialog
from dash.html import Div, Button, H2, Span

from frontend.views.swipe_event_view.swipe_event_view import SwipeEventView
from frontend.views.footstep_view import FootstepView


def build_layout():
    return Div(
        id="page",
        className="page",
        children=[
            # ---------- Header ----------
            Div(
                id="header",
                className="header",
                children=[
                    Div(
                        children=[
                            H2("Swipe Events", id="header-title"),
                            Span(
                                "Footstep extraction QA",
                                id="header-subtitle",
                                className="subtitle",
                            ),
                        ],
                    ),
                    Div(
                        style={"display": "flex", "gap": "8px", "alignItems": "center"},
                        children=[
                            Button(
                                "Swipe Events",
                                id="btn-mode-swipe",
                                className="mode-btn mode-btn-active",
                            ),
                            Button(
                                "Footsteps",
                                id="btn-mode-footstep",
                                className="mode-btn",
                            ),
                            Button(
                                "Run Pipeline",
                                id="btn-mode-pipeline",
                                className="mode-btn",
                            ),
                        ],
                    ),
                ],
            ),
            # ---------- Main Content ----------
            Div(
                id="content",
                className="content",
                children=[
                    # stores
                    Store(
                        id="mode-store",
                        data={"mode": "swipe", "prev_mode": "swipe"},
                        storage_type="session",
                    ),
                    Store(
                        id="scroll-store",
                        data={"swipe": 0, "footstep": 0},
                        storage_type="session",
                    ),
                    Store(
                        id="event-id-store",
                        data={"event_id": None},
                        storage_type="session",
                    ),
                    Store(id="footsteps-store", data=None, storage_type="session"),
                    Store(
                        id="selected-step-store",
                        data={"step_id": None},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_filter_participant_state",
                        data={"prev": []},
                        storage_type="session",
                    ),
                    # UPDATED defaults to match backend metric keys
                    Store(
                        id="metrics_axes_store",
                        data={"x": "avg_box_size", "y": "step_count"},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_scatter_selection_store",
                        data={"event_ids": []},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_selected_events_store",
                        data={"event_ids": []},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_confirmed_events_store",
                        data={"event_ids": []},
                        storage_type="session",
                    ),
                    Store(
                        id="summary-pagination-store",
                        data={"visible_count": 5},
                        storage_type="session",
                    ),
                    Store(
                        id="summary-render-queue-store",
                        data={"pending_ids": [], "total": 0, "visible_total": 0},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_selected_panel_mode_store",
                        data={"mode": "view"},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_selected_checklist_state",
                        data={"prev": []},
                        storage_type="session",
                    ),
                    Store(
                        id="metrics_selected_checklist_store",
                        data={"value": []},
                        storage_type="session",
                    ),
                    # popup for pipeline
                    ConfirmDialog(
                        id="pipeline-dialog",
                        message="Run Pipeline (local) is not implemented yet.",
                    ),
                    # page load trigger
                    Interval(id="page-load", max_intervals=1),
                    Interval(
                        id="summary-render-interval",
                        interval=10,
                        n_intervals=0,
                        max_intervals=0,
                    ),
                    # a hidden sink used by the clientside scroll callback output
                    Div(id="scroll-sink", className="hidden"),
                    # hidden sink (unchanged)
                    Div(
                        id={
                            "type": "dropdown-log-sink",
                            "name": "participant",
                            "level": 4,
                        },
                        className="hidden",
                    ),
                    # views
                    SwipeEventView(),
                    FootstepView(),
                ],
            ),
        ],
    )
