from dash import Input, Output, State, callback

@callback(
    Output("metrics_axes_store", "data"),
    Input("metrics_x_axis", "value"),
    Input("metrics_y_axis", "value"),
    State("metrics_axes_store", "data"),
    prevent_initial_call=False,
)
def save_axes(x_key, y_key, store):
    store = store or {}
    return {"x": x_key or store.get("x", "avg_box_size"),
            "y": y_key or store.get("y", "footstep_count")}
