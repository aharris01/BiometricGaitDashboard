# frontend/views/metrics_graph.py
from __future__ import annotations


from dash import html, dcc
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go

from frontend.views.filters import collapsible_checklist
from frontend.utils import with_select_all
from frontend.api import get_participants


class MetricsGraph:
    # Axis configuration

    AXIS_LABELS = {
        "avg_box_size": "Average Bounding Box Size",
        "footstep_count": "Footstep Count",
        "participant": "Participant ID",
    }
    DEFAULT_POINT_COLOR = "#1f77b4"
    PENDING_POINT_COLOR = "#ff7f0e"
    SELECTED_POINT_COLOR = "#d62728"
    ACTIVE_POINT_COLOR = "#2ca02c"
    DIMMED_POINT_OPACITY = 0.2
    NORMAL_POINT_OPACITY = 1.0

    def __init__(self, swipe_event_metrics: dict | None = None):
        self.metrics = swipe_event_metrics or {}

    def _placeholder_figure(self, text: str, height: int = 440) -> go.Figure:
        fig = go.Figure()
        fig.update_layout(
            height=height,
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor="#e9f0fa",
            paper_bgcolor="#e9f0fa",
            margin=dict(l=0, r=0, t=0, b=0),
            annotations=[
                dict(
                    text=text,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#223a5e", size=14),
                )
            ],
        )
        return fig

    @classmethod
    def build_marker_colors(
        cls,
        event_ids: list[str],
        *,
        pending_event_ids: list[str] | None = None,
        selected_event_ids: list[str] | None = None,
        active_event_id: str | None = None,
    ) -> list[str]:
        normalized_event_ids = [str(eid) for eid in event_ids]
        pending_set = {str(eid) for eid in (pending_event_ids or [])}
        selected_set = {str(eid) for eid in (selected_event_ids or [])}
        normalized_active_id = str(active_event_id) if active_event_id else None

        colors = []
        for eid in normalized_event_ids:
            # Priority: active > selected list > pending scatter > default.
            if eid in selected_set:
                colors.append(cls.SELECTED_POINT_COLOR)
            elif eid in pending_set:
                colors.append(cls.PENDING_POINT_COLOR)
            else:
                colors.append(cls.DEFAULT_POINT_COLOR)

        if normalized_active_id:
            for idx, eid in enumerate(normalized_event_ids):
                if eid == normalized_active_id:
                    colors[idx] = cls.ACTIVE_POINT_COLOR
                    break

        return colors

    @classmethod
    def build_marker_opacities(
        cls,
        event_ids: list[str],
        *,
        pending_event_ids: list[str] | None = None,
        selected_event_ids: list[str] | None = None,
        active_event_id: str | None = None,
    ) -> list[float]:
        normalized_event_ids = [str(eid) for eid in event_ids]
        pending_set = {str(eid) for eid in (pending_event_ids or [])}
        selected_set = {str(eid) for eid in (selected_event_ids or [])}
        normalized_active_id = str(active_event_id) if active_event_id else None

        if not pending_set:
            return [cls.NORMAL_POINT_OPACITY for _ in normalized_event_ids]

        opacities: list[float] = []
        for eid in normalized_event_ids:
            is_emphasized = (
                eid in pending_set
                or eid in selected_set
                or (normalized_active_id is not None and eid == normalized_active_id)
            )
            opacities.append(
                cls.NORMAL_POINT_OPACITY if is_emphasized else cls.DIMMED_POINT_OPACITY
            )

        return opacities

    @classmethod
    def build_selectedpoint_indices(
        cls,
        event_ids: list[str],
        *,
        pending_event_ids: list[str] | None = None,
    ) -> list[int] | None:
        pending_set = {str(eid) for eid in (pending_event_ids or [])}
        if not pending_set:
            return None

        indices = [idx for idx, eid in enumerate(event_ids) if str(eid) in pending_set]
        return indices or None

    def _build_scatter(
        self,
        x_key: str,
        y_key: str,
        *,
        pending_event_ids: list[str] | None = None,
        selected_event_ids: list[str] | None = None,
        active_event_id: str | None = None,
        height: int = 440,
    ) -> go.Figure:
        if not self.metrics:
            return self._placeholder_figure(
                "Summary scatter not available (no metrics data).", height=height
            )

        event_ids: list[str] = []
        x_vals: list[float] = []
        y_vals: list[float] = []

        for eid, m in self.metrics.items():
            x = m.get(x_key)
            y = m.get(y_key)
            if x is None or y is None:
                continue
            event_ids.append(eid)
            x_vals.append(float(x))
            y_vals.append(float(y))

        if not event_ids:
            return self._placeholder_figure(
                "No points available for selected X/Y (missing values).",
                height=height,
            )

        fig = go.Figure()
        marker_colors = self.build_marker_colors(
            event_ids,
            pending_event_ids=pending_event_ids,
            selected_event_ids=selected_event_ids,
            active_event_id=active_event_id,
        )
        marker_opacities = self.build_marker_opacities(
            event_ids,
            pending_event_ids=pending_event_ids,
            selected_event_ids=selected_event_ids,
            active_event_id=active_event_id,
        )
        selectedpoints = self.build_selectedpoint_indices(
            event_ids,
            pending_event_ids=pending_event_ids,
        )
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                marker={"size": 10, "color": marker_colors, "opacity": marker_opacities},
                selectedpoints=selectedpoints,
                text=event_ids,  # event_id used by click/lasso callbacks
                hovertemplate=(
                    "<b>Event:</b> %{text}<br>"
                    + f"<b>{self.AXIS_LABELS.get(x_key, x_key)}:</b> %{{x}}<br>"
                    + f"<b>{self.AXIS_LABELS.get(y_key, y_key)}:</b> %{{y}}"
                    + "<extra></extra>"
                ),
            )
        )

        fig.update_layout(
            height=height,
            xaxis_title=self.AXIS_LABELS.get(x_key, x_key),
            yaxis_title=self.AXIS_LABELS.get(y_key, y_key),
            margin=dict(l=30, r=20, t=10, b=40),
        )
        return fig

    def render(self):
        scatter_plot = self._placeholder_figure(
            "Select X and Y metrics to display scatter.",
            height=440,
        )

        try:
            participant_options = with_select_all(get_participants(logger=None))
        except PreventUpdate:
            participant_options = with_select_all([])

        return html.Div(
            children=[
                html.Div(
                    className="metrics-row",
                    children=[
                        # 1) Filters panel (left)
                        html.Div(
                            className="metrics-panel metrics-panel--filters",
                            children=[
                                dcc.Store(
                                    id="metrics_filter_participant_open_store",
                                    data=True,
                                    storage_type="session",
                                ),
                                html.Div(
                                    className="panel-header",
                                    children=[
                                        html.H3("Filters", className="panel-title"),
                                        html.Button(
                                            "OK",
                                            id="btn-apply-filters",
                                            className="ok-btn",
                                        ),
                                    ],
                                ),
                                collapsible_checklist(
                                    title="by participant",
                                    component_id="metrics_filter_participant",
                                    options=participant_options,
                                    open=True,
                                    details_id="metrics_filter_participant_details",
                                    summary_id="metrics_filter_participant_summary",
                                ),
                            ],
                        ),
                        # 2) Scatter plot (center)
                        html.Div(
                            className="metrics-plot",
                            children=[
                                # ONE LINE: Scatter plot  X: [..]  ⇄  Y: [..]
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "16px",
                                        "marginBottom": "8px",
                                        "flexWrap": "wrap",
                                    },
                                    children=[
                                        html.H3(
                                            "Scatter plot",
                                            className="panel-title",
                                            style={"margin": "0"},
                                        ),
                                        # X
                                        html.Div(
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                                "gap": "6px",
                                            },
                                            children=[
                                                html.Span(
                                                    "X:",
                                                    style={
                                                        "fontWeight": "600",
                                                        "fontSize": "13px",
                                                        "color": "#374151",
                                                    },
                                                ),
                                                dcc.Dropdown(
                                                    id="metrics_x_axis",
                                                    options=[],
                                                    value=None,
                                                    clearable=True,
                                                    className="metrics-axis-dropdown",
                                                    style={"width": "180px"},
                                                ),
                                            ],
                                        ),
                                        # Swap button (between X and Y)
                                        html.Button(
                                            "⇄",
                                            id="btn-swap-axes",
                                            className="mode-btn",
                                            style={
                                                "height": "32px",
                                                "padding": "0 10px",
                                                "fontSize": "14px",
                                            },
                                        ),
                                        # Y
                                        html.Div(
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                                "gap": "6px",
                                            },
                                            children=[
                                                html.Span(
                                                    "Y:",
                                                    style={
                                                        "fontWeight": "600",
                                                        "fontSize": "13px",
                                                        "color": "#374151",
                                                    },
                                                ),
                                                dcc.Dropdown(
                                                    id="metrics_y_axis",
                                                    options=[],
                                                    value=None,
                                                    clearable=True,
                                                    className="metrics-axis-dropdown",
                                                    style={"width": "180px"},
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                dcc.Graph(
                                    id="box-size-scatter-plot",
                                    figure=scatter_plot,
                                    config={
                                        "displayModeBar": True,
                                        "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                                    },
                                    style={"width": "100%", "height": "440px"},
                                ),
                            ],
                        ),
                        # 3) Arrow buttons (middle)
                        html.Div(
                            className="metrics-arrows",
                            children=[
                                html.Button(
                                    "▶", id="btn-add-selected", className="arrow-btn"
                                ),
                                html.Button(
                                    "◀", id="btn-remove-selected", className="arrow-btn"
                                ),
                            ],
                        ),
                        # 4) Selected list (right)
                        html.Div(
                            className="metrics-panel metrics-panel--selected",
                            children=[
                                html.Div(
                                    className="panel-header",
                                    children=[
                                        html.H3("Selected", className="panel-title"),
                                        html.Div(
                                            style={
                                                "display": "flex",
                                                "alignItems": "center",
                                                "gap": "8px",
                                            },
                                            children=[
                                                html.Button(
                                                    "Confirm",
                                                    id="btn-selected-confirm",
                                                    className="ok-btn",
                                                ),
                                                html.Button(
                                                    "Select",
                                                    id="btn-selected-select-mode",
                                                    className="ok-btn",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="metrics-panel-scroll",
                                    children=[
                                        html.Div(
                                            id="metrics-selected-list",
                                            children="(selected items here)",
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                )
            ],
            style={
                "width": "100%",
                "maxWidth": "1350px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "flex-start",
                "margin": "0 auto",
                "paddingBottom": "16px",
            },
        )
