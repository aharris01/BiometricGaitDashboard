# frontend/app.py
import os

from dash import Dash
import plotly.express as px

from frontend.layout import build_layout
from frontend.callbacks import register_all

# colormap
cmap = px.colors.sequential.Jet
cmap[0] = "#000000"

DASH_HOST = os.getenv("DASH_HOST", "127.0.0.1")
DASH_PORT = int(os.getenv("DASH_PORT", "8050"))
DASH_DEBUG = os.getenv("DASH_DEBUG", "false").lower() == "true"

app = Dash(__name__, suppress_callback_exceptions=True)
app.layout = build_layout()

register_all(app, cmap=cmap)


def run_dash() -> None:
    app.run(
        host=DASH_HOST, port=DASH_PORT, debug=DASH_DEBUG, dev_tools_hot_reload=False
    )


if __name__ == "__main__":
    run_dash()
