from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics_x_axis", "value"),
    Output("metrics_y_axis", "value"),
    Input("btn-swap-axes", "n_clicks"),
    State("metrics_x_axis", "value"),
    State("metrics_y_axis", "value"),
    prevent_initial_call=True,
)
def swap_axes(_n, x_key, y_key):
    if not x_key or not y_key:
        raise PreventUpdate
    return y_key, x_key
