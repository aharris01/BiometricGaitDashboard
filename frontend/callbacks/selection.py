# frontend/callbacks/selection.py
from dash import Input, Output, State
from dash.exceptions import PreventUpdate
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


def register(app, *, cmap):
    @app.callback(
        Output("p100-graph", "figure"),
        Output("selected-p100-graph", "figure"),
        Output("selected-grf-graph", "figure"),
        Input("p100-graph", "clickData"),
        State("p100-graph", "figure"),
        State("footsteps-store", "data"),
        State("event-id-store", "data"),
        prevent_initial_call=True,
    )
    def show_selected_step(click_data, figure, footsteps_store, event_store):
        if not click_data or not footsteps_store or not event_store:
            raise PreventUpdate

        event_id = event_store.get("event_id")
        if not event_id:
            raise PreventUpdate

        footsteps = footsteps_store.get("footsteps", [])
        footstep_details = footsteps_store.get("footstep_details", [])

        point = click_data["points"][0]
        x = float(point["x"])
        y = float(point["y"])

        selected = None
        for box in footsteps:
            x_min, x_max = box["x_min"], box["x_max"]
            y_min, y_max = box["y_min"], box["y_max"]

            if x_min <= x <= x_max and y_min <= y <= y_max:
                selected = {
                    "id": box["id"],
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max,
                }
                break

            # fallback if swapped
            if y_min <= x <= y_max and x_min <= y <= x_max:
                selected = {
                    "id": box["id"],
                    "x_min": y_min,
                    "x_max": y_max,
                    "y_min": x_min,
                    "y_max": x_max,
                }
                break

        if selected is None:
            raise PreventUpdate

        step_id = selected["id"]

        # ✅ No API call: read from cached /full payload
        detail = next((d for d in footstep_details if d.get("id") == step_id), None)
        step_p100 = (detail or {}).get("p100", [])
        step_grf = (detail or {}).get("grf", [])

        # highlight selected box on main p100
        fig = figure.copy()
        fig.setdefault("layout", {})
        shapes = list(fig["layout"].get("shapes", []))
        shapes = [shape for shape in shapes if shape.get("name") != "selected_box"]
        shapes.append(
            dict(
                type="rect",
                name="selected_box",
                x0=selected["x_min"],
                x1=selected["x_max"],
                y0=selected["y_min"],
                y1=selected["y_max"],
                line=dict(width=4, color="magenta"),
                fillcolor="rgba(0,0,0,0)",
            )
        )
        fig["layout"]["shapes"] = shapes

        # step p100
        if step_p100:
            step_p100_fig = px.imshow(step_p100, color_continuous_scale=cmap)
            step_p100_fig.update_layout(
                margin=dict(l=20, r=10, t=10, b=40),
                coloraxis_showscale=False,
                height=520,
                width=480,
            )
        else:
            step_p100_fig = go.Figure()
            step_p100_fig.update_layout(
                height=520,
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[
                    dict(
                        text="Step P100 not available.",
                        x=0.5,
                        y=0.5,
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                    )
                ],
            )

        # step grf
        if step_grf:
            grf_arr = np.array(step_grf)
            x_step = np.linspace(0, 100, len(grf_arr))
            step_grf_fig = go.Figure()
            step_grf_fig.add_trace(
                go.Scatter(x=x_step, y=grf_arr, mode="lines", name=f"Step {step_id} GRF")
            )
            step_grf_fig.update_layout(
                title=f"GRF for Step {step_id}",
                xaxis_title="Percentage of Step (%)",
                yaxis_title="Force",
            )
        else:
            step_grf_fig = go.Figure()
            step_grf_fig.update_layout(
                height=300,
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[
                    dict(
                        text="Step GRF not available.",
                        x=0.5,
                        y=0.5,
                        xref="paper",
                        yref="paper",
                        showarrow=False,
                    )
                ],
            )

        return fig, step_p100_fig, step_grf_fig
