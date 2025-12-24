# backend/src/utils/sal.py
from typing import cast, TYPE_CHECKING
from flask import current_app

if TYPE_CHECKING:
    from backend.storage_access_layer.sal import SAL


def get_sal():
    """Get the SAL instance from the current Flask app."""
    sal_obj = current_app.extensions.get("sal")
    if sal_obj is None:
        raise RuntimeError(
            "SAL is not initialized. Ensure create_app() stores it in app.extensions['sal']."
        )
    return cast("SAL", sal_obj)
