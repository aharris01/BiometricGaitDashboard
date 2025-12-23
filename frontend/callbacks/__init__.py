# frontend/callbacks/__init__.py
from .dropdowns import register as register_dropdowns
from .views import register as register_views
from .selection import register as register_selection

def register_all(app, *, cmap):
    register_dropdowns(app)
    register_views(app, cmap=cmap)
    register_selection(app, cmap=cmap)
