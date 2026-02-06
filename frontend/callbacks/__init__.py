from .dropdowns import register as register_dropdowns
from .views import register as register_views
from .selection import register as register_selection
from .modes import register as register_modes
from .metrics_filters import register as register_metrics_filters
from . import filters


def register_all(app, *, cmap):
    register_dropdowns(app)
    register_views(app, cmap=cmap)
    register_selection(app, cmap=cmap)
    register_metrics_filters(app)
    register_modes(app)
