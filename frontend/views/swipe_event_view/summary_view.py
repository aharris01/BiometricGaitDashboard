# frontend/views/swipe_event_view/summary_view.py

from dash import html, dcc
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go

from frontend.api import API_BASE_URL


class SummaryView:
    def __init__(
        self,
        event_id,
        cmap,
        p100_data,
        grf_data=None,
        footsteps=None,
        *,
        step_p100s=None,
        mode="single",
        step_index=0,
    ):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []
        self.footsteps = footsteps or []
        self.step_p100s = step_p100s or []
        self.mode = mode
        self.step_index = int(step_index or 0)

    # ---------------------------------------------------------
    # ID helpers (pattern-matching for multi-event pages)
    # ---------------------------------------------------------

    def _p100_graph_id(self):
        return {"type": "p100-graph", "event_id": str(self.event_id)}

    def _grf_graph_id(self):
        return {"type": "grf-graph", "event_id": str(self.event_id)}

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _placeholder_figure(self, text, height=560):
        fig = go.Figure()
        fig.update_layout(
            height=height,
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor="black",
            paper_bgcolor="black",
            margin=dict(l=0, r=0, t=0, b=0),
            annotations=[
                dict(
                    text=text,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#e5e7eb", size=14),
                )
            ],
        )
        return fig

    def _get_p100_range(self):
        if not self.p100_data or not self.p100_data[0]:
            return (0, 1)

        z_max = 0
        for row in self.p100_data:
            for value in row:
                if value is not None and value > z_max:
                    z_max = value

        return (0, z_max if z_max > 0 else 1)

    def _step_ids_sorted(self):
        ids = [item.get("id") for item in self.step_p100s if item.get("id") is not None]
        return sorted(ids)

    def _get_step_p100(self, step_id):
        for item in self.step_p100s:
            if item.get("id") == step_id:
                return item.get("p100") or []
        return []

    def _get_bbox(self, step_id):
        for box in self.footsteps:
            if box.get("id") == step_id:
                return box
        return None

    def _blank_global_canvas(self):
        if not self.p100_data or not self.p100_data[0]:
            return None

        height = len(self.p100_data)
        width = len(self.p100_data[0])
        return [[0 for _ in range(width)] for _ in range(height)]

    def _resize_nearest(self, img, out_h, out_w):
        if out_h <= 0 or out_w <= 0:
            return []

        in_h = len(img)
        in_w = len(img[0]) if in_h > 0 else 0
        if in_h == 0 or in_w == 0:
            return [[0 for _ in range(out_w)] for _ in range(out_h)]

        out = [[0 for _ in range(out_w)] for _ in range(out_h)]
        for y in range(out_h):
            src_y = int(y * in_h / out_h)
            if src_y >= in_h:
                src_y = in_h - 1
            row = img[src_y]
            for x in range(out_w):
                src_x = int(x * in_w / out_w)
                if src_x >= in_w:
                    src_x = in_w - 1
                out[y][x] = row[src_x]
        return out

    def _global_canvas_for_step(self, step_id):
        """
        Build a full-size black canvas and paste ONE step heatmap into its bbox.
        Used when Show all is OFF.
        """
        canvas = self._blank_global_canvas()
        if canvas is None:
            return None

        bbox = self._get_bbox(step_id)
        if not bbox:
            return canvas

        step_p100 = self._get_step_p100(step_id)
        if not step_p100:
            return canvas

        height = len(canvas)
        width = len(canvas[0])

        x_min = int(bbox["x_min"])
        x_max = int(bbox["x_max"])
        y_min = int(bbox["y_min"])
        y_max = int(bbox["y_max"])

        # clamp bbox
        x_min = max(0, min(x_min, width))
        x_max = max(0, min(x_max, width))
        y_min = max(0, min(y_min, height))
        y_max = max(0, min(y_max, height))

        box_w = x_max - x_min
        box_h = y_max - y_min
        if box_w <= 0 or box_h <= 0:
            return canvas

        step_fit = self._resize_nearest(step_p100, box_h, box_w)

        for yy in range(box_h):
            row = step_fit[yy]
            for xx in range(box_w):
                canvas[y_min + yy][x_min + xx] = row[xx]

        return canvas

    def _bbox_shapes(self, only_step_id=None):
        if not self.p100_data or not self.p100_data[0]:
            return []

        height = len(self.p100_data)
        width = len(self.p100_data[0])

        shapes = []
        for box in self.footsteps:
            if only_step_id is not None and box["id"] != only_step_id:
                continue

            x0, x1, y0, y1 = self._clamp_bbox_to_image(box, width=width, height=height)

            shapes.append(
                dict(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    line=dict(color="rgba(255,0,255,0.9)", width=2),
                    fillcolor="rgba(0,0,0,0)",
                )
            )
        return shapes

    def _clamp_bbox_to_image(self, box, *, width, height):
        x0 = max(0, min(int(box["x_min"]), width - 1))
        x1 = max(0, min(int(box["x_max"]), width - 1))
        y0 = max(0, min(int(box["y_min"]), height - 1))
        y1 = max(0, min(int(box["y_max"]), height - 1))
        return x0, x1, y0, y1

    def _bbox_annotations(self, only_step_id=None):
        annotations = []
        for box in self.footsteps:
            if only_step_id is not None and box["id"] != only_step_id:
                continue
            w = box["x_max"] - box["x_min"]
            h = box["y_max"] - box["y_min"]
            area = int(w * h)
            annotations.append(
                dict(
                    x=box["x_min"],
                    y=box["y_min"],
                    text=f"#{box['id']} ({area})",
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=10, color="magenta"),
                    bgcolor="rgba(255,255,255,0.7)",
                )
            )
        return annotations

    def _global_canvas_for_steps(self, step_ids):
        canvas = self._blank_global_canvas()
        if canvas is None:
            return None

        height = len(canvas)
        width = len(canvas[0])

        for step_id in step_ids:
            bbox = self._get_bbox(step_id)
            if not bbox:
                continue

            step_p100 = self._get_step_p100(step_id)
            if not step_p100:
                continue

            x_min = max(0, min(int(bbox["x_min"]), width))
            x_max = max(0, min(int(bbox["x_max"]), width))
            y_min = max(0, min(int(bbox["y_min"]), height))
            y_max = max(0, min(int(bbox["y_max"]), height))

            box_w = x_max - x_min
            box_h = y_max - y_min
            if box_w <= 0 or box_h <= 0:
                continue

            step_fit = self._resize_nearest(step_p100, box_h, box_w)

            for yy in range(box_h):
                for xx in range(box_w):
                    canvas[y_min + yy][x_min + xx] = step_fit[yy][xx]

        return canvas

    def _render_all_step_grid(self):
        """
        Right panel: clickable thumbnails (IMG), not Plotly graphs.
        These IDs match your callbacks/selection.py (step-thumb + MATCH).
        """
        if not self.step_p100s:
            return html.Div(
                "No extracted footsteps available for this event.",
                style={"fontStyle": "italic", "marginTop": "8px"},
            )

        cards = []
        for item in self.step_p100s:
            step_id = item.get("id")
            if step_id is None:
                continue

            thumb_url = (
                f"{API_BASE_URL}/api/events/{self.event_id}/footsteps/{step_id}/image"
                f"?size=thumb&format=webp"
            )

            cards.append(
                html.Div(
                    children=[
                        html.Div(
                            f"Footstep #{step_id}",
                            style={"fontWeight": "600", "marginBottom": "6px"},
                        ),
                        html.Div(
                            children=[
                                html.Img(
                                    src=thumb_url,
                                    style={
                                        "width": "100%",
                                        "height": "240px",
                                        "objectFit": "contain",
                                        "imageRendering": "pixelated",
                                        "background": "#111",
                                        "borderRadius": "6px",
                                    },
                                )
                            ],
                            id={
                                "type": "step-thumb",
                                "event_id": str(self.event_id),
                                "step_id": step_id,
                            },
                            n_clicks=0,
                            style={"height": "240px", "cursor": "pointer"},
                            title=f"Open footstep {step_id}",
                        ),
                    ],
                    style={
                        "border": "1px solid #e0e0e0",
                        "borderRadius": "8px",
                        "padding": "8px",
                        "background": "white",
                    },
                )
            )

        return html.Div(
            children=cards,
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "12px",
            },
        )

    def _render_grf(self):
        if not self.grf_data:
            return self._placeholder_figure(
                "GRF not available for this event.", height=280
            )

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=list(self.grf_data), mode="lines"))
        fig.update_layout(
            height=280,
            margin=dict(l=30, r=20, t=10, b=30),
            xaxis_title="Frame",
            yaxis_title="GRF",
        )
        return fig

    # ---------------------------------------------------------
    # Render
    # ---------------------------------------------------------

    def render(self):
        step_ids = self._step_ids_sorted()

        if step_ids:
            index = max(0, min(self.step_index, len(step_ids) - 1))
            step_id = step_ids[index]
        else:
            index = 0
            step_id = None

        # Main image mode
        step_ids = self._step_ids_sorted()
        if step_ids:
            index = max(0, min(self.step_index, len(step_ids) - 1))
        else:
            index = 0
        if self.mode == "all":
            image_data = self.p100_data
            shapes = self._bbox_shapes()
            annotations = self._bbox_annotations()
        elif self.mode == "cumulative" and step_ids:
            active_ids = step_ids[: index + 1]
            image_data = self._global_canvas_for_steps(active_ids)
            shapes = []
            annotations = []
            for sid in active_ids:
                shapes += self._bbox_shapes(only_step_id=sid)
                annotations += self._bbox_annotations(only_step_id=sid)
        elif self.mode == "single" and step_ids:
            step_id = step_ids[index]
            image_data = self._global_canvas_for_step(step_id)
            shapes = self._bbox_shapes(only_step_id=step_id)
            annotations = self._bbox_annotations(only_step_id=step_id)
        else:
            image_data = None
            shapes = []
            annotations = []

        # Build P100 figure
        if image_data:
            fig_p100 = px.imshow(image_data, color_continuous_scale=self.cmap)

            z_min, z_max = self._get_p100_range()
            fig_p100.update_traces(zmin=z_min, zmax=z_max)

            fig_p100.update_layout(
                height=560,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_cmin=z_min,
                coloraxis_cmax=z_max,
                shapes=shapes,
                annotations=annotations,
                plot_bgcolor="black",
                paper_bgcolor="white",
                coloraxis_showscale=False,
            )

            fig_p100.update_xaxes(constrain="domain", scaleanchor="y")
            fig_p100.update_yaxes(autorange="reversed", constrain="domain")

            # hide colorbar in single-step mode
            if self.mode != "all":
                fig_p100.update_layout(coloraxis_showscale=False)
        else:
            fig_p100 = self._placeholder_figure(
                "P100 not available for this event.", height=560
            )

        fig_grf = self._render_grf()

        # Top row: left (p100) + right (footsteps)
        top_row = html.Div(
            className="summary-row",
            children=[
                html.Div(
                    className="summary-plot",
                    children=[
                        html.H3(
                            f"Swipe Event Summary: {self.event_id}",
                            className="panel-title",
                            style={"margin": "0 0 8px 0"},
                        ),
                        Graph(
                            id=self._p100_graph_id(),
                            figure=fig_p100,
                            style={"height": "560px"},
                        ),
                        html.Div(
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "alignItems": "center",
                                "gap": "10px",
                                "marginTop": "10px",
                                "width": "100%",
                            },
                            children=[
                                # Row 1: radio centered
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "width": "100%",
                                    },
                                    children=[
                                        dcc.RadioItems(
                                            id={
                                                "type": "summary-mode",
                                                "event_id": str(self.event_id),
                                            },
                                            options=[
                                                {
                                                    "label": "Single step",
                                                    "value": "single",
                                                },
                                                {
                                                    "label": "Cumulative",
                                                    "value": "cumulative",
                                                },
                                                {"label": "Show all", "value": "all"},
                                            ],
                                            value=self.mode,
                                            inline=True,
                                            labelStyle={
                                                "display": "inline-flex",
                                                "alignItems": "center",
                                                "marginRight": "32px",
                                                "gap": "6px",
                                            },
                                        )
                                    ],
                                ),
                                # Row 2: slider centered
                                html.Div(
                                    style={
                                        "display": "flex",
                                        "justifyContent": "center",
                                        "width": "100%",
                                    },
                                    children=[
                                        html.Div(
                                            style={
                                                "width": "100%",
                                                "maxWidth": "680px",
                                            },
                                            children=[
                                                dcc.Slider(
                                                    id={
                                                        "type": "summary-step-slider",
                                                        "event_id": str(self.event_id),
                                                    },
                                                    min=0,
                                                    max=max(len(step_ids) - 1, 0),
                                                    step=1,
                                                    value=index,
                                                    disabled=(
                                                        len(step_ids) <= 1
                                                        or self.mode == "all"
                                                    ),
                                                    marks=None,
                                                    tooltip={
                                                        "placement": "bottom",
                                                        "always_visible": False,
                                                    },
                                                )
                                            ],
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="summary-panel",
                    children=[
                        html.H4(
                            "Footsteps",
                            style={"margin": "0 0 8px 0", "fontWeight": "600"},
                        ),
                        html.Div(
                            className="summary-panel-scroll",
                            children=self._render_all_step_grid(),
                        ),
                    ],
                ),
            ],
        )

        # Bottom row: GRF
        bottom_row = html.Div(
            style={"width": "100%"},
            children=[
                html.Div(
                    children=[
                        html.H3(
                            "GRF",
                            className="panel-title",
                            style={"margin": "0 0 8px 0"},
                        ),
                        Graph(
                            id=self._grf_graph_id(),
                            figure=fig_grf,
                            style={"height": "280px"},
                        ),
                    ],
                    style={
                        "background": "white",
                        "border": "1px solid #e5e7eb",
                        "borderRadius": "8px",
                        "padding": "12px",
                        "boxSizing": "border-box",
                        "width": "100%",
                    },
                )
            ],
        )

        return html.Div(
            id={"type": "summary-view", "event_id": str(self.event_id)},
            children=[top_row, bottom_row],
            style={
                "width": "100%",
                "maxWidth": "1350px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "stretch",
                "margin": "0 auto",
                "paddingBottom": "16px",
            },
        )
