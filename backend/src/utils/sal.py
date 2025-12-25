# backend/src/utils/sal.py
from typing import TYPE_CHECKING, cast
from flask import current_app

if TYPE_CHECKING:
    from backend.storage_access_layer.sal import SAL


def get_sal():
    """Return the SAL instance attached to the current Flask app.

    In tests, backend.src.server.sal may be monkeypatched after the Flask app
    instance is created. To support that, we sync app.extensions["sal"] with the
    module-global server.sal at request time.
    """
    sal_obj = current_app.extensions.get("sal")

    # If tests monkeypatch backend.src.server.sal after app creation,
    # keep the extension in sync so routes use the fake.
    from backend.src import server as server_mod  # local import avoids cycles

    patched = getattr(server_mod, "sal", None)
    if patched is not None and patched is not sal_obj:
        current_app.extensions["sal"] = patched
        sal_obj = patched

    return cast("SAL", sal_obj)
