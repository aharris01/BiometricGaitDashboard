from dash import html, dcc
from dash.dcc import Graph
import plotly.express as px
import plotly.graph_objects as go


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
        show_all=True,
        step_index=0,
    ):
        self.event_id = event_id
        self.cmap = cmap
        self.p100_data = p100_data or []
        self.grf_data = grf_data or []
        self.footsteps = footsteps or []
        self.step_p100s = step_p100s or []
        self.show_all = show_all
        self.step_index = int(step_index or 0)

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
        """
        Nearest-neighbor resize for nested-list 2D arrays.
        Keeps things simple and fast, no numpy required.
        """
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
        Build a full-size black canvas and paste ONE step heatmap
        into its bbox location. If the step thumbnail shape does not
        match bbox size, resize it to fit.
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

        # resize step thumbnail to bbox size so it actually fills the box
        step_fit = self._resize_nearest(step_p100, box_h, box_w)

        for yy in range(box_h):
            row = step_fit[yy]
            for xx in range(box_w):
                canvas[y_min + yy][x_min + xx] = row[xx]

        return canvas

    def _bbox_shapes(self, only_step_id=None):
        shapes = []
        for box in self.footsteps:
            if only_step_id is not None and box["id"] != only_step_id:
                continue
            shapes.append(
                dict(
                    type="rect",
                    x0=box["x_min"],
                    x1=box["x_max"],
                    y0=box["y_min"],
                    y1=box["y_max"],
                    line=dict(color="rgba(255,0,255,0.9)", width=2),
                    fillcolor="rgba(0,0,0,0)",
                )
            )
        return shapes

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

    def _render_all_step_grid(self):
        """
        KEEP your original right-side look:
        - 2-column grid
        - no colorbar
        - 240px cards
        """
        if not self.step_p100s:
            return html.Div(
                "No extracted footsteps available for this event.",
                style={"fontStyle": "italic", "marginTop": "8px"},
            )

        cards = []
        for item in self.step_p100s:
            step_id = item.get("id")
            step_p100 = item.get("p100", [])

            if step_p100:
                fig = px.imshow(step_p100, color_continuous_scale=self.cmap)
                fig.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    coloraxis_showscale=False,
                    height=240,
                )
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False, autorange="reversed")
            else:
                fig = self._placeholder_figure("Step P100 not available.", height=240)

            cards.append(
                html.Div(
                    children=[
                        html.Div(
                            f"Footstep #{step_id}",
                            style={"fontWeight": "600", "marginBottom": "6px"},
                        ),
                        Graph(
                            id={"type": "step-p100", "step_id": step_id},
                            figure=fig,
                            config={"displayModeBar": False},
                            style={"height": "240px", "cursor": "pointer"},
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

        # Left image mode
        if self.show_all:
            image_data = self.p100_data
            shapes = self._bbox_shapes()
            annotations = self._bbox_annotations()
        else:
            image_data = (
                self._global_canvas_for_step(step_id)
                if step_id is not None
                else None
            )
            shapes = (
                self._bbox_shapes(only_step_id=step_id)
                if step_id is not None
                else []
            )
            annotations = (
                self._bbox_annotations(only_step_id=step_id)
                if step_id is not None
                else []
            )

        if image_data:
            fig = px.imshow(image_data, color_continuous_scale=self.cmap)

            z_min, z_max = self._get_p100_range()

            fig.update_traces(zmin=z_min, zmax=z_max)
            fig.update_layout(
                height=560,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_cmin=z_min,
                coloraxis_cmax=z_max,
                shapes=shapes,
                annotations=annotations,
                plot_bgcolor="black",
                paper_bgcolor="white",
            )

            fig.update_xaxes(constrain="domain", scaleanchor="y")
            fig.update_yaxes(autorange="reversed", constrain="domain")

            # hide colorbar in single-step mode (keeps left clean)
            if not self.show_all:
                fig.update_layout(coloraxis_showscale=False)
        else:
            fig = self._placeholder_figure("No data.", height=560)

        return html.Div(
            className="summary-row",
            children=[
                # LEFT: summary plot + controls
                html.Div(
                    className="summary-plot",
                    children=[
                        html.H3(
                            f"Swipe Event Summary: {self.event_id}",
                            className="panel-title",
                            style={"margin": "0 0 8px 0"},
                        ),
                        Graph(
                            id="summary-main-graph",
                            figure=fig,
                            style={"height": "560px"},
                        ),
                        html.Div(
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "16px",
                                "marginTop": "8px",
                            },
                            children=[
                                dcc.Checklist(
                                    id="summary-show-all",
                                    options=[{"label": "Show all", "value": "all"}],
                                    value=["all"] if self.show_all else [],
                                ),
                                dcc.Slider(
                                    id="summary-step-slider",
                                    min=0,
                                    max=max(len(step_ids) - 1, 0),
                                    step=1,
                                    value=index,
                                    disabled=(len(step_ids) <= 1),
                                ),
                            ],
                        ),
                    ],
                ),
                # RIGHT: KEEP ORIGINAL (grid)
                html.Div(
                    className="summary-panel",
                    children=[
                        html.H3(
                            "Footsteps",
                            className="panel-title",
                            style={"margin": "0 0 8px 0"},
                        ),
                        html.Div(
                            className="summary-panel-scroll",
                            children=self._render_all_step_grid(),
                        ),
                    ],
                ),
            ],
        )