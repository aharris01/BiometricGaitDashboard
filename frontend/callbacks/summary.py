# frontend/callbacks/summary.py
from dash import Input, Output, State, callback, MATCH
from dash.exceptions import PreventUpdate

from frontend.api import get_event_full
from frontend.views.swipe_event_view.summary_view import SummaryView


def register(app, *, cmap):
    @callback(
        Output({"type": "summary-view", "event_id": MATCH}, "children"),
        Input({"type": "summary-show-all", "event_id": MATCH}, "value"),
        Input({"type": "summary-step-slider", "event_id": MATCH}, "value"),
        State({"type": "summary-view", "event_id": MATCH}, "id"),
        prevent_initial_call=True,
    )
    def update_summary(show_all_value, step_index, summary_id):
        if not summary_id or "event_id" not in summary_id:
            raise PreventUpdate

        event_id = str(summary_id["event_id"])
        show_all = bool(show_all_value and "all" in show_all_value)

        full = get_event_full(event_id, logger=app.logger)

        return (
            SummaryView(
                event_id,
                cmap,
                full.get("p100", []),
                full.get("grf", []),
                full.get("footsteps", []),
                step_p100s=full.get("footstep_details", []),
                show_all=show_all,
                step_index=int(step_index or 0),
            )
            .render()
            .children
        )
