# frontend/callbacks/filters.py
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics_filter_participant", "value"),
    Input("metrics_filter_participant", "value"),
    State("metrics_filter_participant", "options"),
    prevent_initial_call=True,
)
def toggle_select_all(selected_values, options):
    if not selected_values:
        raise PreventUpdate

    # all real participant values (exclude "__all__")
    all_values = [
        opt["value"]
        for opt in (options or [])
        if opt["value"] != "__all__"
    ]

    # If "Select all" was clicked
    if "__all__" in selected_values:
        # If everything is already selected → clear all
        if set(all_values).issubset(set(selected_values)):
            return []
        # Otherwise → select everything
        return all_values

    return selected_values
