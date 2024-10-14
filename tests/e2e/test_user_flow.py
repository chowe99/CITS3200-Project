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

        # Upload a spreadsheet
        upload_input = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "excel-file"))
        )
        file_path = os.path.abspath("./tests/e2e/test_spreadsheet.xlsx")
        print(f"Uploading file from path: {file_path}")  # Debugging line
        upload_input.send_keys(file_path)

        # Enter encryption password from environment variable
        encrypt_password = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "encrypt_password"))
        )
        encrypt_password.send_keys(os.getenv("TEST_ENCRYPT_PASSWORD", "defaultpassword"))

        # Submit the upload form
        upload_button = browser.find_element(By.XPATH, "//button[text()='Upload and Process']")
        upload_button.click()

        # Wait for the filter form to appear, indicating successful upload
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "filter-form"))
        )

        # Select x-axis and y-axis
        x_axis = browser.find_element(By.NAME, "x_axis")
        x_axis.send_keys("axial_strain")

        y_axis = browser.find_element(By.NAME, "y_axis")
        y_axis.send_keys("shear_induced_pwp")

        # Apply instance filters
        # Step 1: Click the 'Drainage' checkbox to reveal 'Drainage_drained'
        try:
            drainage_checkbox = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.ID, "Drainage"))
            )
            drainage_checkbox.click()
            print("Clicked 'Drainage' checkbox to reveal 'Drainage_drained'.")
        except TimeoutException:
            print("Drainage checkbox not found or not clickable.")
            # Optionally, take a screenshot here for debugging
            browser.save_screenshot("screenshots/drainage_checkbox_not_found.png")
            pytest.fail("Drainage checkbox not found or not clickable.")

        # Step 2: Wait for 'Drainage_drained' to become visible and clickable
        try:
            drainage_drained_checkbox = WebDriverWait(browser, 10).until(
                EC.visibility_of_element_located((By.ID, "Drainage_drained"))
            )
            drainage_drained_checkbox = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.ID, "Drainage_drained"))
            )
            drainage_drained_checkbox.click()
            print("Clicked 'Drainage_drained' checkbox.")
        except TimeoutException:
            print("Drainage_drained checkbox not found or not clickable.")
            # Optionally, take a screenshot here for debugging
            browser.save_screenshot("screenshots/drainage_drained_not_found.png")
            pytest.fail("Drainage_drained checkbox not found or not clickable.")

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
        print("Plot generated successfully.")

    except Exception as e:
        print(f"An exception occurred: {e}")
        # Take a screenshot for debugging purposes
        browser.save_screenshot("screenshots/test_failure.png")
        raise e


def test_upload_and_plot_with_preset_option(browser):
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

        # Step 3: Wait for the table to appear in the non-encrypted section
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "non-encrypted-tables"))
        )
        print("Non-encrypted tables section is visible.")

        # DEBUG: Print the contents of the non-encrypted tables section
        non_encrypted_tables_section = browser.find_element(By.ID, "non-encrypted-tables")
        print(f"Non-encrypted tables section HTML: {non_encrypted_tables_section.get_attribute('innerHTML')}")

        # Step 4: Select the uploaded spreadsheet from the non-encrypted tables section
        try:
            table_checkbox = WebDriverWait(browser, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@name='table_name[]'][@value='test_1']"))
            )
            table_checkbox.click()
            print("Selected the uploaded spreadsheet (test_1.xlsx) from the non-encrypted tables.")
        except TimeoutException:
            print("Failed to find the checkbox for test_1.xlsx.")
            # Take a screenshot for debugging purposes
            browser.save_screenshot("screenshots/checkbox_not_found.png")
            pytest.fail("Checkbox for test_1.xlsx not found in non-encrypted tables section.")

        # Step 5: Select preset plot option
        preset_dropdown = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.NAME, "preset-options"))
        )
        preset_dropdown.send_keys("Vol strain vs axial strain")
        print("Selected 'Vol strain vs axial strain' preset option.")

        # Step 6: Press the "Generate Plot" button
        generate_button = browser.find_element(By.XPATH, "//button[text()='Generate Plot']")
        generate_button.click()
        print("Clicked 'Generate Plot' button.")

        # Step 7: Wait for plot generation
        WebDriverWait(browser, 30).until(
            EC.presence_of_element_located((By.ID, "plot-container"))
        )

        # Step 8: Validate the plot
        plot_container = browser.find_element(By.ID, "plot-container")
        assert plot_container is not None
        print("Plot generated successfully.")

        # Step 9: Take a screenshot on success
        browser.save_screenshot("screenshots/success_plot_generated.png")
        print("Screenshot taken and saved at 'screenshots/success_plot_generated.png'.")

    except Exception as e:
        print(f"An exception occurred: {e}")
        # Take a screenshot for debugging purposes on failure
        browser.save_screenshot("screenshots/test_failure.png")
        raise e
