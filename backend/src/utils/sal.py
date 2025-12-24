# backend/src/utils/sal.py
from typing import TYPE_CHECKING, cast

from flask import current_app

if TYPE_CHECKING:
    from backend.storage_access_layer.sal import SAL


def get_sal():
    """Return the SAL instance for the current app.

    - Prefer the Flask app extension: current_app.extensions["sal"]
    - If it's missing, fall back to backend.src.server.get_sal(), then
      store it on the app for future calls.
    """
    sal_obj = current_app.extensions.get("sal")
    if sal_obj is None:
        from backend.src import server as server_mod  # local import to avoid cycles

        sal_obj = server_mod.get_sal()
        current_app.extensions["sal"] = sal_obj

    return cast("SAL", sal_obj)
