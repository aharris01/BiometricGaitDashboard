# frontend/views/footstep_view.py
from dash.html import Div


def FootstepView():
    return Div(
        id="footstep-view",
        className="hidden",
        children=[
            Div(
                "Footsteps mode (coming soon).",
                style={
                    "padding": "24px",
                    "background": "white",
                    "borderRadius": "8px",
                    "border": "1px solid #e5e7eb",
                    "color": "#6b7280",
                },
            )
        ],
    )
