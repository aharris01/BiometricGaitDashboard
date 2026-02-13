# frontend/callbacks/filters.py
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics_filter_participant", "value"),
    Output("metrics_filter_participant_state", "data"),
    Input("metrics_filter_participant", "value"),
    State("metrics_filter_participant", "options"),
    State("metrics_filter_participant_state", "data"),
    prevent_initial_call=True,
)
def participant_select_all(curr_values, options, state):
    curr_values = curr_values or []
    prev_values = (state or {}).get("prev", [])

    if not options:
        raise PreventUpdate

    all_values = [o["value"] for o in options if o["value"] != "__all__"]
    all_set = set(all_values)

    curr_has_all = "__all__" in curr_values
    prev_has_all = "__all__" in prev_values

    curr_real = [v for v in curr_values if v != "__all__"]
    curr_real_set = set(curr_real)

    # 1) User checked "Select all"
    if curr_has_all and not prev_has_all:
        new_values = ["__all__"] + all_values
        return new_values, {"prev": new_values}

    # 2) User unchecked "Select all"
    if not curr_has_all and prev_has_all:
        new_values = []
        return new_values, {"prev": new_values}

    # 3) "Select all" is checked, but user unchecked some item
    if curr_has_all and not all_set.issubset(curr_real_set):
        new_values = curr_real  # remove "__all__"
        return new_values, {"prev": new_values}

    # 4) User manually selected all items -> auto-check "Select all"
    if not curr_has_all and all_set.issubset(curr_real_set) and all_values:
        new_values = ["__all__"] + all_values
        return new_values, {"prev": new_values}

    return curr_values, {"prev": curr_values}
