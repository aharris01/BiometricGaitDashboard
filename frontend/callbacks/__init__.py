from .views import register as register_views
from .selection import register as register_selection
from .modes import register as register_modes
from .metrics_filters import register as register_metrics_filters
from .summary import register as register_summary
from .footsteps import register as register_footsteps
from . import filters  # noqa: F401
from . import metrics_selection  # noqa: F401
from . import scatter_click  # noqa: F401
from . import selected_panel  # noqa: F401
from . import selected_checklist_select_all  # noqa: F401
from . import swap_axes  # noqa: F401
from . import axes  # noqa: F401


def register_all(app, *, cmap):
    register_views(app, cmap=cmap)
    register_selection(app, cmap=cmap)
    register_metrics_filters(app)
    register_modes(app)
    register_summary(app, cmap=cmap)
    register_footsteps(app)
