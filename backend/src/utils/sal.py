# backend/src/utils/sal.py
from typing import TYPE_CHECKING, cast
from flask import current_app

if TYPE_CHECKING:
    from backend.storage_access_layer.sal import SAL


def get_sal():
    """
    Routes should always read SAL from current_app.extensions["sal"].
    server.create_app() is responsible for putting it there.
    """
    return cast("SAL", current_app.extensions["sal"])
