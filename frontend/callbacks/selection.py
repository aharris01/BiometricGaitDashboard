# frontend/callbacks/selection.py
from dash import Input, Output, State, ALL, ctx
from dash.exceptions import PreventUpdate

PINK = "rgba(255,0,255,0.9)"
GREEN = "rgba(0,200,0,0.95)"


def register(app, *, cmap):
    @app.callback(
        Output("p100-graph", "figure"),
        Output("selected-step-store", "data"),
        Input({"type": "step-p100", "step_id": ALL}, "clickData"),
        State("p100-graph", "figure"),
        State("footsteps-store", "data"),
        prevent_initial_call=True,
    )
    def click_thumbnail_highlight_bbox(_all_clicks, p100_fig, footsteps_store):
        triggered = ctx.triggered_id
        if not triggered or "step_id" not in triggered:
            raise PreventUpdate

        step_id = triggered["step_id"]

        if not p100_fig or not footsteps_store:
            raise PreventUpdate

        footsteps = footsteps_store.get("footsteps", [])
        if not footsteps:
            raise PreventUpdate

        # rebuild shapes: selected -> green, others -> pink
        new_shapes = []
        for box in footsteps:
            color = GREEN if box.get("id") == step_id else PINK
            new_shapes.append(
                dict(
                    type="rect",
                    name="bbox",
                    x0=box["x_min"],
                    x1=box["x_max"],
                    y0=box["y_min"],
                    y1=box["y_max"],
                    line=dict(color=color, width=3),
                    fillcolor="rgba(0,0,0,0)",
                )
            )

        fig = p100_fig.copy()
        fig.setdefault("layout", {})
        fig["layout"]["shapes"] = new_shapes

        return fig, {"step_id": step_id}
