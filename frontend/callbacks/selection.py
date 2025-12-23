# frontend/callbacks/selection.py
from dash import Input, Output, State
from dash.exceptions import PreventUpdate
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from frontend.api import API_BASE, fetch_json

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
    def show_selected_step(clickData, figure, footsteps, event_store):
        if not clickData or not footsteps or not event_store:
            raise PreventUpdate

        event_id = event_store.get("event_id")
        if not event_id:
            raise PreventUpdate

        point = clickData["points"][0]
        x = float(point["x"])
        y = float(point["y"])

        selected = None

        for box in footsteps:
            xm, xM = box["x_min"], box["x_max"]
            ym, yM = box["y_min"], box["y_max"]

            if xm <= x <= xM and ym <= y <= yM:
                selected = {"id": box["id"], "x_min": xm, "x_max": xM, "y_min": ym, "y_max": yM}
                break

            # fallback if swapped
            if ym <= x <= yM and xm <= y <= xM:
                selected = {"id": box["id"], "x_min": ym, "x_max": yM, "y_min": xm, "y_max": xM}
                break

        if selected is None:
            raise PreventUpdate

        step_id = selected["id"]

        data = fetch_json(f"{API_BASE}/api/events/{event_id}/footsteps/{step_id}", context="getFootstepDetail", logger=app.logger)
        step_p100 = data.get("p100", [])
        step_grf = data.get("grf", [])

        # highlight box on main p100 (keep existing shapes if present)
        fig = figure.copy()
        fig.setdefault("layout", {})
        shapes = list(fig["layout"].get("shapes", []))
        shapes = [s for s in shapes if s.get("name") != "selected_box"]
        shapes.append(
            dict(
                type="rect",
                name="selected_box",
                x0=selected["x_min"], x1=selected["x_max"],
                y0=selected["y_min"], y1=selected["y_max"],
                line=dict(width=4, color="magenta"),
                fillcolor="rgba(0,0,0,0)",
            )
        )
        fig["layout"]["shapes"] = shapes

        # step p100
        if step_p100:
            step_p100_fig = px.imshow(step_p100, color_continuous_scale=cmap)
            step_p100_fig.update_layout(margin=dict(l=20, r=10, t=10, b=40), coloraxis_showscale=False, height=520, width=480)
        else:
            step_p100_fig = go.Figure()
            step_p100_fig.update_layout(
                height=520,
                xaxis={"visible": False}, yaxis={"visible": False},
                annotations=[dict(text="Step P100 not available.", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
            )

        # step grf
        if step_grf:
            grf_arr = np.array(step_grf)
            x_step = np.linspace(0, 100, len(grf_arr))
            step_grf_fig = go.Figure()
            step_grf_fig.add_trace(go.Scatter(x=x_step, y=grf_arr, mode="lines", name=f"Step {step_id} GRF"))
            step_grf_fig.update_layout(title=f"GRF for Step {step_id}", xaxis_title="Percentage of Step (%)", yaxis_title="Force")
        else:
            step_grf_fig = go.Figure()
            step_grf_fig.update_layout(
                height=300,
                xaxis={"visible": False}, yaxis={"visible": False},
                annotations=[dict(text="Step GRF not available.", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
            )

        return fig, step_p100_fig, step_grf_fig
