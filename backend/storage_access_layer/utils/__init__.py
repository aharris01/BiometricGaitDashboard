import os
from pathlib import Path
from urllib.parse import unquote, urlparse


def uri_to_path(uri: str) -> Path:
    """
    Accept:
      - file:// URIs
      - plain filesystem paths

    Reject:
      - any other URI scheme (http://, s3://, etc.)
    """
    s = str(uri)

    if "://" in s and not s.startswith("file://"):
        raise ValueError(f"Unsupported URI scheme in {uri!r}; expected file://")

    if not s.startswith("file://"):
        return Path(s)

    parsed = urlparse(s)
    path = unquote(parsed.path)

    # Windows: "/C:/Users/..." -> "C:/Users/..."
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]

    return Path(path)
