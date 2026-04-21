import pytest
import os

BASE_URL = "http://localhost:8000"

# These are optional end-to-end UI tests. They assume:
# - The FastAPI server is already running on localhost:8000
# - A browser + driver is available
# Enable via RUN_UI_TESTS=1 (handled in conftest).
pytestmark = pytest.mark.ui

if os.getenv("RUN_UI_TESTS", "").strip().lower() not in {"1", "true", "yes", "on"}:
    pytest.skip("UI tests disabled. Set RUN_UI_TESTS=1 to enable.", allow_module_level=True)

selenium = pytest.importorskip("selenium")
webdriver_manager = pytest.importorskip("webdriver_manager")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_homepage_loads(browser):
    browser.get(BASE_URL)
    assert "AutoSocial AI" in browser.title

def test_folder_monitoring(browser):
    browser.get(f"{BASE_URL}/monitor")
    folder_input = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "folder-path"))
    )
    folder_input.send_keys("D:/test-folder")
    submit_btn = browser.find_element(By.ID, "start-monitoring")
    submit_btn.click()
    status = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "monitoring-status"))
    )
    assert "Monitoring active" in status.text

def test_content_generation(browser):
    browser.get(f"{BASE_URL}/generate")
    trigger_btn = browser.find_element(By.ID, "generate-content")
    trigger_btn.click()
    content = WebDriverWait(browser, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "generated-content"))
    )
    assert content.text != ""

def test_post_scheduling(browser):
    browser.get(f"{BASE_URL}/schedule")
    date_input = browser.find_element(By.ID, "schedule-date")
    date_input.send_keys("2024-12-31")
    schedule_btn = browser.find_element(By.ID, "schedule-post")
    schedule_btn.click()
    confirmation = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "schedule-confirmation"))
    )
    assert "Post scheduled" in confirmation.text

def test_api_configuration(browser):
    browser.get(f"{BASE_URL}/settings")
    api_key = browser.find_element(By.ID, "openai-key")
    api_key.send_keys("test-key")
    save_btn = browser.find_element(By.ID, "save-settings")
    save_btn.click()
    success_message = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "settings-saved"))
    )
    assert "Settings saved" in success_message.text
