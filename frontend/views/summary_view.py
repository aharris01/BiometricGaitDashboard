# frontend/views/summary_view.py
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

    def _placeholder_figure(self, text, height=560):
        fig = go.Figure()
        fig.update_layout(
            height=height,
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor="#e9f0fa",
            paper_bgcolor="#e9f0fa",
            margin=dict(l=0, r=0, t=0, b=0),
            annotations=[dict(text=text, x=0.5, y=0.5, xref="paper", yref="paper",
                              showarrow=False, font=dict(color="#223a5e", size=14))],
        )
        return fig

    def _step_ids_sorted(self):
        ids = [it.get("id") for it in self.step_p100s if it.get("id") is not None]
        return sorted(ids)

    def _get_step_p100(self, step_id: int):
        for it in self.step_p100s:
            if it.get("id") == step_id:
                return it.get("p100") or []
        return []

    def _get_bbox(self, step_id: int):
        for b in self.footsteps:
            if b.get("id") == step_id:
                return b
        return None

    def _bbox_shapes(self, *, only_step_id=None):
        shapes = []
        for b in self.footsteps:
            if only_step_id is not None and b["id"] != only_step_id:
                continue
            shapes.append(
                dict(
                    type="rect",
                    x0=b["x_min"],
                    x1=b["x_max"],
                    y0=b["y_min"],
                    y1=b["y_max"],
                    line=dict(color="rgba(255,0,255,0.9)", width=2),
                    fillcolor="rgba(0,0,0,0)",
                )
            )
        return shapes

    def _bbox_annotations(self, *, only_step_id=None):
        anns = []
        for b in self.footsteps:
            if only_step_id is not None and b["id"] != only_step_id:
                continue
            w = b["x_max"] - b["x_min"]
            h = b["y_max"] - b["y_min"]
            area = int(w * h)
            anns.append(
                dict(
                    x=b["x_min"],
                    y=b["y_min"],
                    text=f"#{b['id']} ({area})",
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=10, color="magenta"),
                    bgcolor="rgba(255,255,255,0.7)",
                )
            )
        return anns

    def _blank_global_canvas(self):
        if not self.p100_data or not self.p100_data[0]:
            return None
        H = len(self.p100_data)
        W = len(self.p100_data[0])
        return [[0 for _ in range(W)] for _ in range(H)]

    def _global_canvas_for_step(self, step_id: int):
        canvas = self._blank_global_canvas()
        if canvas is None:
            return None

        bbox = self._get_bbox(step_id)
        if not bbox:
            return canvas

        step_p100 = self._get_step_p100(step_id)
        if not step_p100:
            return canvas

        H = len(canvas)
        W = len(canvas[0])

        x0, x1 = int(bbox["x_min"]), int(bbox["x_max"])
        y0, y1 = int(bbox["y_min"]), int(bbox["y_max"])

        # clamp to canvas
        x0 = max(0, min(x0, W))
        x1 = max(0, min(x1, W))
        y0 = max(0, min(y0, H))
        y1 = max(0, min(y1, H))

        h_crop = min(y1 - y0, len(step_p100))
        w_crop = min(x1 - x0, len(step_p100[0]) if step_p100 else 0)

        for yy in range(h_crop):
            row = step_p100[yy]
            for xx in range(w_crop):
                canvas[y0 + yy][x0 + xx] = row[xx]

        return canvas

    def _render_step_grid(self):
        if not self.step_p100s:
            return html.Div("No extracted footsteps available.", style={"fontStyle": "italic"})

        cards = []
        for it in self.step_p100s:
            step_id = it.get("id")
            step_p100 = it.get("p100") or []

            if step_p100:
                fig = px.imshow(step_p100, color_continuous_scale=self.cmap)
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10),
                                  coloraxis_showscale=False, height=220)
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False, autorange="reversed")
            else:
                fig = self._placeholder_figure("N/A", height=220)

            cards.append(
                html.Div(
                    children=[
                        html.Div(f"Footstep #{step_id}", style={"fontWeight": "600", "marginBottom": "6px"}),
                        Graph(
                            id={"type": "step-p100", "step_id": step_id},
                            figure=fig,
                            config={"displayModeBar": False},
                            style={"height": "220px"},
                        ),
                    ],
                    style={"border": "1px solid #e0e0e0", "borderRadius": "8px", "padding": "8px", "background": "white"},
                )
            )

        return html.Div(children=cards, style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"})

    def render(self):
        step_ids = self._step_ids_sorted()
        if step_ids:
            idx = max(0, min(self.step_index, len(step_ids) - 1))
            step_id = step_ids[idx]
        else:
            idx = 0
            step_id = None

        # build left image
        if self.show_all:
            img = self.p100_data
            shapes = self._bbox_shapes()
            anns = self._bbox_annotations()
        else:
            img = self._global_canvas_for_step(step_id) if step_id is not None else None
            shapes = self._bbox_shapes(only_step_id=step_id) if step_id is not None else []
            anns = self._bbox_annotations(only_step_id=step_id) if step_id is not None else []

        if img:
            fig = px.imshow(img, color_continuous_scale=self.cmap)
            fig.update_layout(
                height=560,
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_colorbar=dict(thickness=18, xpad=0),
                shapes=shapes,
                annotations=anns,
            )
            fig.update_xaxes(constrain="domain", scaleanchor="y")
            fig.update_yaxes(autorange="reversed", constrain="domain")
        else:
            fig = self._placeholder_figure("No data.")

        return html.Div(
            className="summary-row",
            children=[
                html.Div(
                    className="summary-plot",
                    children=[
                        html.H3(f"Swipe Event Summary: {self.event_id}", className="panel-title", style={"margin": "0 0 8px 0"}),
                        Graph(id="summary-main-graph", figure=fig, style={"height": "560px"}),
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "16px", "marginTop": "8px"},
                            children=[
                                dcc.Checklist(
                                    id="summary-show-all",
                                    options=[{"label": "Show all", "value": "all"}],
                                    value=["all"] if self.show_all else [],
                                    style={"fontSize": "13px"},
                                ),
                                html.Div(
                                    style={"flex": "1"},
                                    children=[
                                        dcc.Slider(
                                            id="summary-step-slider",
                                            min=0,
                                            max=max(len(step_ids) - 1, 0),
                                            step=1,
                                            value=idx,
                                            marks=None,
                                            tooltip={"placement": "bottom"},
                                            disabled=(len(step_ids) <= 1),
                                        ),
                                        dcc.Store(id="summary-step-ids-store", data=step_ids, storage_type="memory"),
                                        html.Div(
                                            id="summary-step-label",
                                            children=(f"Footstep: {step_id}" if (not self.show_all and step_id is not None) else ""),
                                            style={"fontSize": "12px", "color": "#6b7280", "marginTop": "4px"},
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    className="summary-panel",
                    children=[
                        html.H3("Footsteps", className="panel-title", style={"margin": "0 0 8px 0"}),
                        html.Div(className="summary-panel-scroll", children=self._render_step_grid()),
                    ],
                ),
            ],
        )