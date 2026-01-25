import pytest
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.mark.parametrize("start_mode", ["swipe", "footstep"])
def test_mode_switching_updates_header_and_views(dash_duo, start_mode):
    """
    Covers:
    - default mode (swipe)
    - switching to footstep
    - switching back to swipe
    - header title/subtitle updates
    - hide/show class toggles
    - active button styling
    """
    from frontend.app import app

    dash_duo.start_server(app)

    def el(css):
        return dash_duo.find_element(css)

    def has_hidden(div_id: str) -> bool:
        cls = el(f"#{div_id}").get_attribute("class") or ""
        return "hidden" in cls.split()

    dash_duo.wait_for_text_to_equal("#header-title", "Swipe Events", timeout=5)
    assert el("#header-subtitle").text.strip() == "Footstep extraction QA"

    assert has_hidden("swipe-view") is False
    assert has_hidden("footstep-view") is True

    swipe_btn_cls = el("#btn-mode-swipe").get_attribute("class") or ""
    footstep_btn_cls = el("#btn-mode-footstep").get_attribute("class") or ""
    assert "mode-btn-active" in swipe_btn_cls
    assert "mode-btn-active" not in footstep_btn_cls

    if start_mode == "footstep":
        el("#btn-mode-footstep").click()

        dash_duo.wait_for_text_to_equal("#header-title", "Footsteps", timeout=5)
        assert el("#header-subtitle").text.strip() == "Footstep-level inspection"

        assert has_hidden("swipe-view") is True
        assert has_hidden("footstep-view") is False

        swipe_btn_cls = el("#btn-mode-swipe").get_attribute("class") or ""
        footstep_btn_cls = el("#btn-mode-footstep").get_attribute("class") or ""
        assert "mode-btn-active" not in swipe_btn_cls
        assert "mode-btn-active" in footstep_btn_cls

    el("#btn-mode-footstep").click()

    dash_duo.wait_for_text_to_equal("#header-title", "Footsteps", timeout=5)
    assert el("#header-subtitle").text.strip() == "Footstep-level inspection"

    assert has_hidden("swipe-view") is True
    assert has_hidden("footstep-view") is False

    swipe_btn_cls = el("#btn-mode-swipe").get_attribute("class") or ""
    footstep_btn_cls = el("#btn-mode-footstep").get_attribute("class") or ""
    assert "mode-btn-active" not in swipe_btn_cls
    assert "mode-btn-active" in footstep_btn_cls

    el("#btn-mode-swipe").click()

    dash_duo.wait_for_text_to_equal("#header-title", "Swipe Events", timeout=5)
    assert el("#header-subtitle").text.strip() == "Footstep extraction QA"

    assert has_hidden("swipe-view") is False
    assert has_hidden("footstep-view") is True

    swipe_btn_cls = el("#btn-mode-swipe").get_attribute("class") or ""
    footstep_btn_cls = el("#btn-mode-footstep").get_attribute("class") or ""
    assert "mode-btn-active" in swipe_btn_cls
    assert "mode-btn-active" not in footstep_btn_cls


def test_run_pipeline_shows_popup_and_does_not_switch_mode(dash_duo):
    """
    Covers the pipeline branch:
    - clicking Run Pipeline triggers browser confirm dialog (ConfirmDialog)
    - mode/view should remain unchanged after closing the dialog
    """
    from frontend.app import app

    dash_duo.start_server(app)

    dash_duo.wait_for_text_to_equal("#header-title", "Swipe Events", timeout=5)

    dash_duo.find_element("#btn-mode-footstep").click()
    dash_duo.wait_for_text_to_equal("#header-title", "Footsteps", timeout=5)

    dash_duo.find_element("#btn-mode-pipeline").click()

    # Wait for native confirm dialog to appear (ConfirmDialog uses browser alert)
    alert = WebDriverWait(dash_duo.driver, 5).until(EC.alert_is_present())
    msg = alert.text
    alert.accept()

    assert "Run Pipeline" in msg

    dash_duo.wait_for_text_to_equal("#header-title", "Footsteps", timeout=5)

    swipe_cls = dash_duo.find_element("#swipe-view").get_attribute("class") or ""
    footstep_cls = dash_duo.find_element("#footstep-view").get_attribute("class") or ""
    assert "hidden" in swipe_cls
    assert "hidden" not in footstep_cls
