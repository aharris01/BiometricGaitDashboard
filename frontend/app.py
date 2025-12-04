from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    callback,
    ctx,
    no_update,
)
from dash.dcc import Dropdown, Interval, Store
from dash.html import Div, Button
from dash.exceptions import PreventUpdate, MissingCallbackContextException
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

from frontend.views.summary_view import SummaryView

# Define the color map to be used in the graphs
cmap = px.colors.sequential.Jet
cmap[0] = "#000000"  # Set the 0 value of the color map to black

API_BASE = "http://127.0.0.1:8000"
CONTROL_STYLE = {"flex": "1", "minWidth": "160px"}

# allow callbacks that reference dynamically-created components
app = Dash(__name__, suppress_callback_exceptions=True)


def require_values(context, **kwargs):
    missing = [name for name, value in kwargs.items() if value is None]
    if missing:
        print(
            f"[{context}] Missing parameters: {', '.join(missing)}; skipping data fetch."
        )
        raise PreventUpdate


def parse_date_str(s: str):
    fmt = "%Y-%m-%d"
    try:
        return bool(datetime.strptime(s, fmt))
    except ValueError:
        return False


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


def calculate_cascade_state(triggered_id, all_ids, all_values):
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
                opts = fetch_options_for_level(current_level, current_selections)
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


def fetch_options_for_level(target_level, upstream_selections):
    participant = upstream_selections.get(4)
    datestr = upstream_selections.get(3)
    direction = upstream_selections.get(2)

    if target_level == 3 and participant:
        return fetch_dates(participant)
    elif target_level == 2 and datestr:
        return fetch_directions(participant, datestr)
    elif target_level == 1 and direction:
        return fetch_events(participant, datestr, direction)
    return []


def fetch_dates(participant):
    require_values(context="Get Dates", participant=participant)
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates", context="getDates"
    )
    return [{"label": str(d), "value": str(d)} for d in data["items"]]


def fetch_directions(participant, datestr):
    require_values(context="Get Directions", participant=participant, datestr=datestr)
    data = fetch_json(
        f"{API_BASE}/api/participants/{participant}/dates/{datestr}/directions",
        context="getDirections",
    )
    return [{"label": str(dir_), "value": dir_} for dir_ in data["items"]]


def fetch_events(participant, datestr, direction):
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


# ----------------- Layout -----------------

app.layout = Div(
    id="page",
    style={
        "height": "100vh",
        "overflowY": "auto",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "flex-start",
        "padding": "16px",
        "boxSizing": "border-box",
        "gap": "4px",
    },
    children=[
        Div(
            id={"type": "dropdown-log-sink", "name": "participant", "level": 4},
            style={"display": "none"},
        ),
        Store(id="event-id-store", data={"event_id": None}, storage_type="session"),
        Store(id="footsteps-store", data=None, storage_type="session"),
        Interval(id="page-load", max_intervals=1),
        Div(
            id="dropdown-container",
            style={
                "width": "100%",
                "maxWidth": "900px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "gap": "8px",
            },
            children=[
                Dropdown(
                    id={"type": "dropdown", "name": "participant", "level": 4},
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
        Div(id="summary-container", style={"marginTop": "0"}),
    ],
)


# ----------------- Callbacks -----------------

@callback(
    Output({"type": "dropdown", "name": "participant", "level": 4}, "options"),
    Output({"type": "dropdown", "name": "participant", "level": 4}, "value"),
    Input("page-load", "n_intervals"),
    prevent_initial_call=False,
)
def fetch_participants(_):
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
    if not ctx.triggered_id:
        return no_update, no_update
    return calculate_cascade_state(
        triggered_id=ctx.triggered_id, all_ids=ids, all_values=values
    )


@callback(
    Output("event-id-store", "data"),
    Input("submit-button", "n_clicks"),
    State({"type": "dropdown", "name": "participant", "level": 4}, "value"),
    State({"type": "dropdown", "name": "date", "level": 3}, "value"),
    State({"type": "dropdown", "name": "direction", "level": 2}, "value"),
    State({"type": "dropdown", "name": "event", "level": 1}, "value"),
    prevent_initial_call=True,
)
def getSwipeEventId(_, participant, datestr, direction, event):
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
        f"{API_BASE}/api/swipe/{participant}/{datestr}/{direction}/{event}",
        context="getSwipeEventId",
    )
    event_id = data["id"]
    app.logger.warning(f"Swipe Event ID: {event_id}")
    return {"event_id": event_id}



@callback(
    Output("summary-container", "children"),
    Output("footsteps-store", "data"),
    Input("event-id-store", "data"),
    prevent_initial_call=True,
)
def display_summary_graph(store_data):
    # Don’t run until we have an event_id
    if not store_data or not store_data.get("event_id"):
        raise PreventUpdate

    event_id = store_data["event_id"]

    # Fetch P100
    p100_resp = fetch_json(
        f"{API_BASE}/api/events/{event_id}/p100", context="getEventP100"
    )
    p100 = p100_resp.get("p100", [])

    # Fetch trial GRF
    grf_resp = fetch_json(
        f"{API_BASE}/api/events/{event_id}/grf", context="getEventGRF"
    )
    grf = grf_resp.get("grf", [])

    # Fetch footsteps metadata (list of boxes)
    footsteps = fetch_json(
        f"{API_BASE}/api/events/{event_id}/footsteps/data",
        context="getFootsteps",
    )

    view = SummaryView(event_id, cmap, p100, grf).render()
    return view, footsteps



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
    # ---- Debug prints ----
    print("---- show_selected_step called ----")
    print("clickData:", clickData)
    print("event_store:", event_store)
    print("footsteps (first 3):", footsteps[:3] if footsteps else footsteps)

    if not clickData or not footsteps or not event_store:
        raise PreventUpdate

    event_id = event_store.get("event_id")
    if not event_id:
        raise PreventUpdate

    # Clicked coordinates on the P100 heatmap
    point = clickData["points"][0]
    x = float(point["x"])
    y = float(point["y"])
    print(f"clicked at x={x}, y={y}")

    selected = None
    mapping_used = None

    # Try to find which step's bounding box contains this point
    for box in footsteps:
        # Expect keys: x_min, x_max, y_min, y_max
        xm, xM = box["x_min"], box["x_max"]
        ym, yM = box["y_min"], box["y_max"]

        # Mapping A: (x_min/x_max) are true x (columns), (y_min/y_max) are true y (rows)
        if xm <= x <= xM and ym <= y <= yM:
            selected = {
                "id": box["id"],
                "x_min": xm,
                "x_max": xM,
                "y_min": ym,
                "y_max": yM,
            }
            mapping_used = "xy"
            break

        # Mapping B: swapped (just in case metadata is flipped)
        if ym <= x <= yM and xm <= y <= xM:
            selected = {
                "id": box["id"],
                "x_min": ym,
                "x_max": yM,
                "y_min": xm,
                "y_max": xM,
            }
            mapping_used = "yx_swapped"
            break

    print("selected box:", selected, "mapping_used:", mapping_used)

    if selected is None:
        # Click outside any box → nothing to update
        raise PreventUpdate

    step_id = selected["id"]

    # ---- Call backend for per-step P100 + GRF ----
    url = f"{API_BASE}/api/events/{event_id}/footsteps/{step_id}"
    data = fetch_json(url, context="getFootstepDetail")

    step_p100 = data.get("p100", [])
    step_grf = data.get("grf", [])

    # ---- 1) Highlight bounding box on main P100 ----
    fig = figure.copy()
    fig.setdefault("layout", {})
    # Ensure shapes list exists
    if "shapes" not in fig["layout"]:
        fig["layout"]["shapes"] = []
    else:
        fig["layout"]["shapes"] = []

    fig["layout"]["shapes"].append(
        {
            "type": "rect",
            "x0": selected["x_min"],
            "y0": selected["y_min"],
            "x1": selected["x_max"],
            "y1": selected["y_max"],
            "line": {"width": 3, "color": "cyan"},
            "fillcolor": "rgba(0,0,0,0)",
        }
    )

    # ---- 2) step P100 ----
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

    # ---- 3) step GRF ----
    if step_grf:
        grf_arr = np.array(step_grf)
        x_step = np.linspace(0, 100, len(grf_arr))
        step_grf_fig = px.line(
            x=x_step,
            y=grf_arr,
            labels={"x": "Percentage of Step (%)", "y": "Force"},
            title=f"GRF for Step {step_id}",
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

def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True, dev_tools_hot_reload=False)
