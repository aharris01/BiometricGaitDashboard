import pytest
from dash.exceptions import PreventUpdate
from frontend.utils import require_values, parse_date_str


@pytest.mark.unit
def test_require_values_raises_when_missing():
    with pytest.raises(PreventUpdate):
        require_values("test", a=None, b=1)


@pytest.mark.unit
def test_require_values_passes_when_all_present():
    require_values("test", a=1, b=2)


@pytest.mark.unit
def test_parse_date_str_valid():
    assert parse_date_str("2024-10-01") is True


@pytest.mark.unit
def test_parse_date_str_invalid():
    assert parse_date_str("2024/10/01") is False
