from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate


@callback(
    Output("metrics_selected_checklist", "value"),
    Output("metrics_selected_checklist_state", "data"),
    Output("metrics_selected_checklist_store", "data"),
    Input("metrics_selected_checklist", "value"),
    State("metrics_selected_checklist", "options"),
    State("metrics_selected_checklist_state", "data"),
    prevent_initial_call=True,
)
def selected_list_select_all(curr_values, options, state):
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

    # checked select-all
    if curr_has_all and not prev_has_all:
        new_values = ["__all__"] + all_values
        return new_values, {"prev": new_values}, {"value": new_values}

    # unchecked select-all
    if not curr_has_all and prev_has_all:
        new_values = []
        return new_values, {"prev": new_values}, {"value": new_values}

    # select-all checked but user unchecked something
    if curr_has_all and not all_set.issubset(curr_real_set):
        new_values = curr_real
        return new_values, {"prev": new_values}, {"value": new_values}

    # user manually selected all -> auto check select-all
    if not curr_has_all and all_set.issubset(curr_real_set) and all_values:
        new_values = ["__all__"] + all_values
        return new_values, {"prev": new_values}, {"value": new_values}

    return curr_values, {"prev": curr_values}, {"value": curr_values}
