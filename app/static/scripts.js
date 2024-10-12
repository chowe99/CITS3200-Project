async function showMessage(message, isSuccess, elementId) {
  const messageArea = document.getElementById(elementId);
  if (messageArea) {
    messageArea.textContent = message;
    messageArea.style.color = isSuccess ? "green" : "red";
    messageArea.style.display = message ? "block" : "none"; // Hide if message is empty
  }
}

// Handle the upload form submission
document
  .getElementById("upload-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    try {
      const response = await fetch("/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        // Display success message
        await showMessage(data.message, true, "message-area");
        // Refresh the table list
        await refreshTableList();
      } else {
        // Display error message
        await showMessage(data.message, false, "message-area");
      }
    } catch (error) {
      console.error("Error:", error);
      await showMessage(
        "An error occurred while uploading the file.",
        false,
        "message-area",
      );
    }
  });

// Function to refresh the table list after uploading new spreadsheets
async function refreshTableList() {
  try {
    const response = await fetch("/get-tables");
    const data = await response.json();
    const tableCheckboxes = document.getElementById("table-checkboxes");
    tableCheckboxes.innerHTML = ""; // Clear existing options
    data.tables.forEach((table) => {
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.name = "table_name[]";
      checkbox.value = table;

      const label = document.createElement("label");
      label.textContent = table;

      tableCheckboxes.appendChild(checkbox);
      tableCheckboxes.appendChild(label);
      tableCheckboxes.appendChild(document.createElement("br"));
    });
  } catch (error) {
    console.error("Error fetching table list:", error);
    await showMessage("Error fetching table list.", false, "message-area");
  }
}

// Handle filter form submission (combined table and instance filters)
document
  .getElementById("filter-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);

    // Collect selected tables
    const selectedTables = Array.from(
      document.querySelectorAll('input[name="table_name[]"]:checked'),
    ).map((checkbox) => checkbox.value);

    // Collect selected instances and their values
    const instances = [];
    document.querySelectorAll('input[name="instances"]').forEach((checkbox) => {
      const instanceName = checkbox.value;
      const selectedValues = [];
      document
        .querySelectorAll(`input[name="${instanceName}_values"]:checked`)
        .forEach((valueCheckbox) => {
          selectedValues.push(valueCheckbox.value);
        });
      if (selectedValues.length > 0) {
        instances.push({ name: instanceName, values: selectedValues });
      }
    });

    // Include selected tables and instances in form data
    selectedTables.forEach((table) => formData.append("table_name[]", table));
    formData.append("instances", JSON.stringify(instances));

    // Determine which filters are applied based on user's selection
    const filterType = document.getElementById("form-select").value;
    formData.append("filter_type", filterType);

    try {
      const response = await fetch("/load-filters", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (data.success) {
        // Update plot options and display plot form
        document.getElementById("plot-form").style.display = "block";
        await updatePlotOptions(data.x_axis_options, data.y_axis_options);

        // Store the filtered spreadsheet IDs for plotting
        const filteredSpreadsheetIds = data.filtered_spreadsheet_ids;
        const hiddenInput = document.getElementById("filtered-spreadsheet-ids");
        hiddenInput.value = JSON.stringify(filteredSpreadsheetIds);
      } else {
        await showMessage(data.message, false, "message-area");
      }
    } catch (error) {
      console.error("Error:", error);
      await showMessage(
        "An error occurred while applying filters.",
        false,
        "message-area",
      );
    }
  });

// Function to update plot options based on loaded columns
async function updatePlotOptions(xOptions, yOptions) {
  const xAxisSelect = document.querySelector('select[name="x_axis"]');
  const yAxisContainer = document.getElementById("y-axis-container");

  // Clear current options
  xAxisSelect.innerHTML = "";
  yAxisContainer.innerHTML = "";

  // Populate new options for X-Axis
  xOptions.forEach((column) => {
    const option = document.createElement("option");
    option.value = column;
    option.textContent = column;
    xAxisSelect.appendChild(option);
  });

  // Populate new checkboxes for Y-Axis
  yOptions.forEach((column) => {
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "y_axis";
    checkbox.value = column;

    const label = document.createElement("label");
    label.textContent = column;

    yAxisContainer.appendChild(checkbox);
    yAxisContainer.appendChild(label);
    yAxisContainer.appendChild(document.createElement("br"));
  });
}

// Handle the plot form submission
document
  .getElementById("plot-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const x_axis_value = document.querySelector('select[name="x_axis"]').value;

    // Ensure x_axis value is not empty before appending
    if (x_axis_value) {
      formData.append("x_axis", x_axis_value);
    } else {
      await showMessage(
        "Please select an X-Axis value.",
        false,
        "plot-message-area",
      );
      return;
    }

    // Get filtered spreadsheet IDs from hidden input
    const filteredSpreadsheetIds = document.getElementById(
      "filtered-spreadsheet-ids",
    ).value;
    formData.append("filtered_spreadsheet_ids", filteredSpreadsheetIds);

    // Get decryption password
    const decryptPassword = document.getElementById("decrypt_password").value;
    formData.append("decrypt_password", decryptPassword);

    try {
      const response = await fetch("/plot", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.graph_json) {
        const plotData = JSON.parse(data.graph_json);
        Plotly.react("plot-container", plotData.data, plotData.layout);
        await showMessage(
          "Plot generated successfully.",
          true,
          "plot-message-area",
        );
      } else if (data.error) {
        await showMessage(data.error, false, "plot-message-area");
      } else {
        await showMessage(
          "An unknown error occurred.",
          false,
          "plot-message-area",
        );
      }
    } catch (error) {
      console.error("Error:", error);
      await showMessage("Error generating plot.", false, "plot-message-area");
    }
  });

// Function to show or hide forms based on filter selection
async function showSelectedForm() {
  const selectedForm = document.getElementById("form-select").value;
  const spreadsheetSelection = document.getElementById("spreadsheet-selection");
  const instanceSelection = document.getElementById("instance-selection");

  if (selectedForm === "table") {
    spreadsheetSelection.style.display = "block";
    instanceSelection.style.display = "none";
  } else if (selectedForm === "instance") {
    spreadsheetSelection.style.display = "none";
    instanceSelection.style.display = "block";
  } else {
    spreadsheetSelection.style.display = "block";
    instanceSelection.style.display = "block";
  }
}

// Initialize form visibility on page load
window.onload = async () => {
  await showSelectedForm();
};

// Event listener for filter type selection
document.getElementById("form-select").addEventListener("change", async () => {
  await showSelectedForm();
});

// Function to toggle visibility of instance value checklists
async function toggleValueChecklist(checkbox) {
  const valueChecklist =
    checkbox.parentElement.querySelector(".value-checklist");
  if (checkbox.checked) {
    valueChecklist.style.display = "block";
  } else {
    valueChecklist.style.display = "none";
    const valueCheckboxes = valueChecklist.querySelectorAll(
      'input[type="checkbox"]',
    );
    valueCheckboxes.forEach((cb) => (cb.checked = false));
  }
}

// Clear messages when forms are changed
document
  .getElementById("upload-form")
  .addEventListener("change", async function () {
    await showMessage("", true, "message-area"); // Clear the message area
  });

document
  .getElementById("plot-form")
  .addEventListener("change", async function () {
    await showMessage("", true, "plot-message-area"); // Clear the plot message area
  });

// Show add columns when button is clicked
document.getElementById("add-column-btn").addEventListener("click", function() {
document.getElementById("add-column-modal").style.display = "block"; // Show the modal
});