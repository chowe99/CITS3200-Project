# tests/e2e/test_user_flow.py

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

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
    try:
        # Retrieve the base URL from environment variables, default to localhost
        base_url = os.getenv("BASE_URL", "http://localhost:5123")
        browser.get(base_url)

        # Step 1: Upload the spreadsheet (test_1.xlsx)
        upload_input = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "excel-file"))
        )
        file_path = os.path.abspath("./tests/e2e/test_1.xlsx")
        print(f"Uploading file from path: {file_path}")  # Debugging line
        upload_input.send_keys(file_path)

        # Step 2: Submit the upload form
        upload_button = browser.find_element(By.XPATH, "//button[text()='Upload and Process']")
        upload_button.click()
        print("Uploaded test_1.xlsx and clicked 'Upload and Process' button.")

        # Step 3: Wait for the non-encrypted tables section to appear
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "non-encrypted-tables"))
        )
        print("Non-encrypted tables section is visible.")

        # Step 4: Check if the uploaded file `test_1` appears in the non-encrypted section
        try:
            table_checkbox = WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='table_name[]'][@value='test_1']"))
            )
            print("test_1 was uploaded successfully and is available in the non-encrypted tables.")
        except TimeoutException:
            print("Failed to find the checkbox for test_1. Upload may have failed.")
            # Take a screenshot for debugging purposes
            browser.save_screenshot("screenshots/test_1_not_found.png")
            pytest.fail("Checkbox for test_1 not found in non-encrypted tables. Possible upload failure.")

        # Step 5: Select the uploaded spreadsheet (test_1)
        table_checkbox.click()
        print("Selected the uploaded spreadsheet (test_1) from the non-encrypted tables.")

        # Step 6: Select preset plot option
        preset_dropdown = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.NAME, "preset-options"))
        )
        preset_dropdown.send_keys("Vol strain vs axial strain")
        print("Selected 'Vol strain vs axial strain' preset option.")

        # Step 7: Press the "Generate Plot" button
        generate_button = browser.find_element(By.XPATH, "//button[text()='Generate Plot']")
        generate_button.click()
        print("Clicked 'Generate Plot' button.")

        # Step 8: Wait for plot generation
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "plot-container"))
        )

        # Step 9: Validate the plot
        plot_container = browser.find_element(By.ID, "plot-container")
        assert plot_container is not None
        print("Plot generated successfully.")

        # Step 10: Take a screenshot on success
        browser.save_screenshot("screenshots/success_plot_generated.png")
        print("Screenshot taken and saved at 'screenshots/success_plot_generated.png'.")

    except Exception as e:
        print(f"An exception occurred: {e}")
        # Take a screenshot for debugging purposes on failure
        browser.save_screenshot("screenshots/test_failure.png")
        raise e