import os

import pytest


def _ui_tests_enabled() -> bool:
    return os.getenv("RUN_UI_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}

@pytest.fixture(scope="function")
def browser():
    if not _ui_tests_enabled():
        pytest.skip("UI tests disabled. Set RUN_UI_TESTS=1 to enable.")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ModuleNotFoundError:
        pytest.skip("UI test dependencies not installed (selenium/webdriver-manager).")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.maximize_window()
    yield driver
    driver.quit()
