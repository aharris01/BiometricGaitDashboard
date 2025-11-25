from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    callback,
    dcc,
    ctx,
    MATCH,
    ALLSMALLER,
    no_update,
)
from dash.dcc import Dropdown, Interval, Store
from dash.html import Div, Button
from dash.exceptions import PreventUpdate
import requests
import plotly.express as px
from datetime import datetime
from frontend.views import summary_view


def parse_date_str(s: str):
    format = "%Y-%m-%d"
    res = True
    try:
        res = bool(datetime.strptime(s, format))
    except ValueError:
        res = False

    return res


def calculate_cascade_state(triggered_id, all_ids, all_values):
    """
    Determines the new state (values and options) for ALL dropdowns
    based on which dropdown triggered the change.

    Returns:
        tuple: (list_of_new_values, list_of_new_options)
    """
    # 1. Setup: Identify the trigger and current selections
    trigger_level = triggered_id.get("level", 0) if triggered_id else 0

    # Map current selections {level: value} for easy lookup
    current_selections = {
        id_dict.get("level"): val for id_dict, val in zip(all_ids, all_values)
    }
    trigger_value = current_selections.get(trigger_level)

    new_values = []
    new_options = []

    # 2. Logic Loop: Determine fate of each component
    for component_id, current_val in zip(all_ids, all_values):
        current_level = component_id.get("level", 0)

        # --- Logic: Am I the "Next Step" in the chain? ---
        if current_level == trigger_level - 1:
            if trigger_value is None:
                # Parent cleared -> Clear me
                new_values.append(None)
                new_options.append([])
            else:
                # Parent selected -> Populate me
                opts = fetch_options_for_level(current_level, current_selections)
                new_values.append(None)  # Reset value
                new_options.append(opts)

        # --- Logic: Am I further downstream? ---
        elif current_level < trigger_level - 1:
            # If I have data, I must be cleared because my ancestor changed
            if current_val is not None:
                new_values.append(None)
                new_options.append([])
            else:
                new_values.append(no_update)
                new_options.append(no_update)

        # --- Logic: Am I upstream or the trigger itself? ---
        else:
            new_values.append(no_update)
            new_options.append(no_update)

    return new_values, new_options


API_BASE = "http://127.0.0.1:8000"
CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}

app = Dash(__name__)


def fetch_json(url, *, timeout=5, context="API request"):
    """Fetch JSON from the API and log readable errors"""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        message = f"[{context}] Failed to fetch {url}: {exc}"
        app.logger.error(message)
        raise PreventUpdate


app.layout = Div(
    id="page",
    style={
        "minHeight": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "flex-start",
        "padding": "16px",
        "boxSizing": "border-box",
        "gap": "24px",
    },
    children=[
        Div(
            id={"type": "dropdown-log-sink", "name": "participant", "level": 4},
            style={"display": "none"},
        ),
        Store(id="event-id-store", data={"event_id": None}, storage_type="session"),
        Interval(id="page-load", max_intervals=1),
        Div(
            id="dropdown-container",
            style={
                "height": "15vh",
                "width": "100%",
                "maxWidth": "900px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "gap": "8px",
            },
            children=[
                Dropdown(
                    id={
                        "type": "dropdown",
                        "name": "participant",
                        "level": 4,
                    },
                    style=CONTROL_STYLE,
                    clearable=True,
                ),
                Dropdown(
                    id={"type": "dropdown", "name": "date", "level": 3},
                    style=CONTROL_STYLE,
                    clearable=True,
                ),
                Dropdown(
                    id={"type": "dropdown", "name": "direction", "level": 2},
                    style=CONTROL_STYLE,
                    clearable=True,
                ),
                Dropdown(
                    id={"type": "dropdown", "name": "event", "level": 1},
                    style=CONTROL_STYLE,
                    clearable=True,
                ),
                Button(
                    id="submit-button",
                    n_clicks=0,
                    children="Submit",
                    style={"height": "38px", "padding": "0 24px"},
                ),
                Div(id="button-pressed"),
            ],
        ),
        Div(
            dcc.Graph(id="p100-graph"),
            style={
                "height": "75vh",
                "maxWidth": "1500px",
                "flex": "1",
                "display": "flex",
                "justifyContent": "center",
            },
        ),
    ],
)


# @callback(Output("button-pressed", "children"), Input("submit-button", "n_clicks"))
# def numberOfClicks(n_clicks):
#     return f"Button clicked {n_clicks} times"


@callback(
    Output({"type": "dropdown", "name": "participant", "level": 4}, "options"),
    Output({"type": "dropdown", "name": "participant", "level": 4}, "value"),
    Input("page-load", "n_intervals"),
    prevent_initial_call=False,
)
def getParticipants(_):
    app.logger.warning("Page loaded")
    data = fetch_json(f"{API_BASE}/api/participants", context="getParticipants")
    options = [{"label": str(p), "value": p} for p in data["items"]]
    first_value = options[0]["value"] if options else None
    return options, first_value


@callback(
    Output(
        {"type": "dropdown", "name": ALL, "level": ALL}, "value", allow_duplicate=True
    ),
    Output(
        {"type": "dropdown", "name": ALL, "level": ALL}, "options", allow_duplicate=True
    ),
    Input({"type": "dropdown", "name": ALL, "level": ALL}, "value"),
    State({"type": "dropdown", "name": ALL, "level": ALL}, "id"),
    prevent_initial_call=True,
)
def manage_dropdown_cascade(values, ids):
    # Guard clause for safety
    if not ctx.triggered_id:
        return no_update, no_update

    # Delegate to the pure Python function
    return calculate_cascade_state(
        triggered_id=ctx.triggered_id, all_ids=ids, all_values=values
    )


def fetch_options_for_level(target_level, upstream_selections):
    """
    name: one of "date", "direction", "event"
    target_level: Which dropdown was changed
    upstream_selection: dict object with {level: value} for lookup
    returns a list of {label, value} dicts
    """
    participant = upstream_selections.get(4)
    datestr = upstream_selections.get(3)
    direction = upstream_selections.get(2)

    if target_level == 3 and participant:
        require_values(context="Get Dates", participant=participant)
        data = fetch_json(
            f"{API_BASE}/api/participants/{participant}/dates", context="getDates"
        )
        dates = [{"label": str(d), "value": str(d)} for d in data["items"]]
        return dates

    elif target_level == 2 and datestr:
        require_values(
            context="Get Directions", participant=participant, datestr=datestr
        )
        data = fetch_json(
            f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions",
            context="getDirections",
        )
        return [{"label": str(dir_), "value": dir_} for dir_ in data["items"]]

    elif target_level == 1 and direction:
        require_values(
            context="Get Events",
            participant=participant,
            datestr=datestr,
            direction=direction,
        )
        data = fetch_json(
            f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions/{direction}/events",
            context="getEvents",
        )
        return [{"label": str(e), "value": e} for e in data["items"]]

    return []


# @callback(
#     Output("event-id-store", "data"),
#     Input("submit-button", "n_clicks"),
#     State({"type": "dropdown", "name": "participant", "level": 4}, "value"),
#     State({"type": "dropdown", "name": "date", "level": 3}, "value"),
#     State({"type": "dropdown", "name": "direction", "level": 2}, "value"),
#     State({"type": "dropdown", "name": "event", "level": 1}, "value"),
# )
# def getSwipeEventId(_, participant, datestr, direction, event):
#     trigger = ctx.triggered_id or "<no trigger>"
#     app.logger.warning(
#         "Get Swipe Event ID - triggered=%s; inputs=%s",
#         ctx.triggered,
#         ctx.inputs,
#     )
#     require_values(
#         context=f"Get Swipe Event - Trigger: {trigger}",
#         participant=participant,
#         datestr=datestr,
#         direction=direction,
#         event=event,
#     )
#     data = fetch_json(
#         f"{API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}",
#         context="getSwipeEventId",
#     )
#     event_id = data["id"]
#     return {"event_id": event_id}


# # Define the color map to be used in the graphs
# cmap = px.colors.sequential.Jet
# cmap[0] = "#000000"  # Set the 0 value of the color map to black


# @app.callback(
#     Output("p100-graph", "figure"),
#     Input("event-id-store", "data"),
#     prevent_initial_call=True,
# )
# def display_summary_graph(store_data):
#     trigger = ctx.triggered_id or "<no trigger>"
#     app.logger.warning(
#         "Update Graph - triggered=%s; inputs=%s",
#         ctx.triggered,
#         ctx.inputs,
#     )
#     require_values(
#         context=f"Update Graph - Trigger: {trigger}",
#         store_data=store_data,
#     )
#     if store_data is None or store_data.get("event_id") is None:
#         raise PreventUpdate
#     event_id = store_data["event_id"]
#     data = fetch_json(
#         f"{API_BASE}/api/events/{event_id}/p100",
#         context="display_summary_graph",
#     )
#     trial = data["p100"]
#     if trial == []:
#         app.logger.warning("No P100 returned")
#         raise PreventUpdate
#     fig = px.imshow(trial, color_continuous_scale=cmap)
#     return fig


def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)


def require_values(context, **kwargs):
    missing = [name for name, value in kwargs.items() if value is None]
    if missing:
        print(
            f"[{context}] Missing parameters: {', '.join(missing)}; skipping data fetch."
        )
        raise PreventUpdate
