# tests/e2e/test_user_flow.py

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import os

@pytest.fixture(scope="session")
def browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()

def test_upload_and_plot(browser):
    # Navigate to the application
    browser.get("http://localhost:5123")

    # Upload a spreadsheet
    upload_input = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, "excel-file"))
    )
    file_path = os.path.abspath("./tests/e2e/test_spreadsheet.xlsx")
    print(f"Uploading file from path: {file_path}")  # Debugging line
    upload_input.send_keys(file_path)

    # Enter encryption password from environment variable
    encrypt_password = browser.find_element(By.ID, "encrypt_password")
    encrypt_password.send_keys(os.getenv("TEST_ENCRYPT_PASSWORD", "defaultpassword"))

    # Submit the upload form
    upload_button = browser.find_element(By.XPATH, "//button[text()='Upload and Process']")
    upload_button.click()

   # Wait for a success message or redirect
    WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.ID, "filter-form"))
    )
    # Select filters and plotting options
    # Example: Select x-axis and y-axis
    x_axis = browser.find_element(By.NAME, "x_axis")
    x_axis.send_keys("axial_strain")

    y_axis = browser.find_element(By.NAME, "y_axis")
    y_axis.send_keys("shear_induced_pwp")

    # Apply instance filters
    drainage_filter = browser.find_element(By.ID, "drained")
    drainage_filter.click()

    # Submit the plot form
    plot_button = browser.find_element(By.XPATH, "//button[text()='Generate Plot']")
    plot_button.click()

     # Wait for plot generation
    WebDriverWait(browser, 30).until(
        EC.presence_of_element_located((By.ID, "plot-container"))
    )

    # Validate plot presence
    plot_container = browser.find_element(By.ID, "plot-container")
    assert plot_container is not None

