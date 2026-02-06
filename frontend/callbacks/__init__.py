from .dropdowns import register as register_dropdowns
from .views import register as register_views
from .selection import register as register_selection
from .modes import register as register_modes
from . import filters


def register_all(app, *, cmap):
    register_dropdowns(app)
    register_views(app, cmap=cmap)
    register_selection(app, cmap=cmap)
    register_modes(app)
