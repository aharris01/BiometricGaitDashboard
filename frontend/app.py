# frontend/app.py
import os
import logging

from dash import Dash, Input, Output, State
import plotly.express as px

from frontend.layout import build_layout
from frontend.callbacks import register_all

# colormap
cmap = px.colors.sequential.Jet
cmap[0] = "#000000"

DASH_HOST = os.getenv("DASH_HOST", "127.0.0.1")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))
DASH_DEBUG = os.getenv("DASH_DEBUG", "false").lower() == "true"

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
)
app.layout = build_layout()

register_all(app, cmap=cmap)

app.clientside_callback(
    """
    function(modeData, scrollData) {
        const mode = (modeData && modeData.mode) ? modeData.mode : "swipe";
        const prev = (modeData && modeData.prev_mode) ? modeData.prev_mode : mode;

        const store = scrollData || { swipe: 0, footstep: 0 };

        // Save scroll position for the mode we are leaving
        store[prev] = window.scrollY || 0;

        // Restore scroll position for the mode we are entering
        const y = store[mode] || 0;
        window.scrollTo(0, y);

        // Must return something for Dash output; store is updated
        return [store, ""];
    }
    """,
    Output("scroll-store", "data"),
    Output("scroll-sink", "children"),
    Input("mode-store", "data"),
    State("scroll-store", "data"),
)


def run_dash(debug_mode: bool = False) -> None:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    app.run(
        host=DASH_HOST,
        port=DASH_PORT,
        debug=debug_mode,
        dev_tools_hot_reload=debug_mode,
    )


if __name__ == "__main__":
    run_dash(True)
