# frontend/app.py
from dash import Dash
import plotly.express as px

from frontend.layout import build_layout
from frontend.callbacks import register_all

# colormap
cmap = px.colors.sequential.Jet
cmap[0] = "#000000"

app = Dash(__name__, suppress_callback_exceptions=True)
app.layout = build_layout()

register_all(app, cmap=cmap)

def runDash():
    app.run(host="127.0.0.1", port=8050, debug=False)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=True, dev_tools_hot_reload=False)
