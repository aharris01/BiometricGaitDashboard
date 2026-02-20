# frontend/callbacks/dropdowns.py
from dash import ALL, Input, Output, State, callback, ctx, no_update
from dash.exceptions import MissingCallbackContextException

from frontend.api import (
    API_BASE_URL,
    fetch_json,
    get_participants,
    get_dates,
    get_directions,
    get_events,
)
from frontend.utils import require_values


def _fetch_options_for_level(target_level, upstream, logger):
    participant = upstream.get(4)
    datestr = upstream.get(3)
    direction = upstream.get(2)

    if target_level == 3 and participant:
        return get_dates(participant, logger=logger)
    if target_level == 2 and participant and datestr:
        return get_directions(participant, datestr, logger=logger)
    if target_level == 1 and participant and datestr and direction:
        return get_events(participant, datestr, direction, logger=logger)
    return []


def _calculate_cascade_state(triggered_id, all_ids, all_values, logger):
    trigger_level = triggered_id.get("level", 0) if triggered_id else 0
    current_selections = {
        id_dict.get("level"): val for id_dict, val in zip(all_ids, all_values)
    }
    trigger_value = current_selections.get(trigger_level)

    new_values = []
    new_options = []

    for component_id, current_val in zip(all_ids, all_values):
        current_level = component_id.get("level", 0)

        if current_level == trigger_level - 1:
            if trigger_value is None:
                new_values.append(None)
                new_options.append([])
            else:
                opts = _fetch_options_for_level(
                    current_level, current_selections, logger
                )
                new_values.append(None)
                new_options.append(opts)

        elif current_level < trigger_level - 1:
            if current_val is not None:
                new_values.append(None)
                new_options.append([])
            else:
                new_values.append(no_update)
                new_options.append(no_update)
        else:
            new_values.append(no_update)
            new_options.append(no_update)

    return new_values, new_options


def register(app):
    @callback(
        Output({"type": "dropdown", "name": "participant", "level": 4}, "options"),
        Output({"type": "dropdown", "name": "participant", "level": 4}, "value"),
        Input("page-load", "n_intervals"),
        prevent_initial_call=False,
    )
    def fetch_participants(_):
        app.logger.warning("Page loaded")
        options = get_participants(logger=app.logger)
        first_value = options[0]["value"] if options else None
        return options, first_value

    @callback(
        Output(
            {"type": "dropdown", "name": ALL, "level": ALL},
            "value",
            allow_duplicate=True,
        ),
        Output(
            {"type": "dropdown", "name": ALL, "level": ALL},
            "options",
            allow_duplicate=True,
        ),
        Input({"type": "dropdown", "name": ALL, "level": ALL}, "value"),
        State({"type": "dropdown", "name": ALL, "level": ALL}, "id"),
        prevent_initial_call=True,
    )
    def manage_dropdown_cascade(values, ids):
        if not ctx.triggered_id:
            return no_update, no_update

        # --- sort by level (highest -> lowest) to make logic stable ---
        indexed = list(enumerate(zip(ids, values)))
        indexed_sorted = sorted(
            indexed, key=lambda t: (t[1][0].get("level", 0)), reverse=True
        )

        ids_sorted = [pair[0] for _, pair in indexed_sorted]
        values_sorted = [pair[1] for _, pair in indexed_sorted]
        orig_indices = [i for i, _ in indexed_sorted]

        # run your existing logic on sorted lists
        new_values_sorted, new_options_sorted = _calculate_cascade_state(
            ctx.triggered_id, ids_sorted, values_sorted, app.logger
        )

        # --- unsort back to Dash’s original order ---
        n = len(ids)
        new_values = [no_update] * n
        new_options = [no_update] * n
        for sorted_pos, original_pos in enumerate(orig_indices):
            new_values[original_pos] = new_values_sorted[sorted_pos]
            new_options[original_pos] = new_options_sorted[sorted_pos]

        return new_values, new_options

    @callback(
        Output("none", "data"),
        # Output("event-id-store","data"),
        Input("submit-button", "n_clicks"),
        State({"type": "dropdown", "name": "participant", "level": 4}, "value"),
        State({"type": "dropdown", "name": "date", "level": 3}, "value"),
        State({"type": "dropdown", "name": "direction", "level": 2}, "value"),
        State({"type": "dropdown", "name": "event", "level": 1}, "value"),
        prevent_initial_call=True,
    )
    def get_swipe_event_id(_, participant, datestr, direction, event):
        try:
            trigger = ctx.triggered_id or "<no trigger>"
            app.logger.warning(
                "Get Swipe Event ID - triggered=%s; inputs=%s",
                ctx.triggered,
                ctx.inputs,
            )
        except MissingCallbackContextException:
            trigger = "<no trigger>"
            app.logger.warning(
                "Get Swipe Event ID called outside callback context; trigger=%s",
                trigger,
            )

        require_values(
            context=f"Get Swipe Event - Trigger: {trigger}",
            participant=participant,
            datestr=datestr,
            direction=direction,
            event=event,
        )

        data = fetch_json(
            f"{API_BASE_URL}/api/swipe/{participant}/{datestr}/{direction}/{event}",
            context="get_swipe_event_id",
            logger=app.logger,
        )
        event_id = data["id"]
        app.logger.warning("Swipe Event ID: %s", event_id)
        return {"event_id": event_id}
