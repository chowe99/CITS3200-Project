let selectedTableName = ""; // Variable to store the selected table name

function showMessage(message, isSuccess, elementId) {
  const messageArea = document.getElementById(elementId);
  if (messageArea) {
    messageArea.textContent = message;
    messageArea.style.color = isSuccess ? "green" : "red";
    messageArea.style.display = "block";
  }
}

// JavaScript to handle table selection and plot form display
document
  .getElementById("table-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    selectedTableNames = formData.getAll("table_name[]"); // Store the selected table name
    try {
      const response = await fetch("/load-table", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      console.log("AJAX Response Data:", data); // Debug log for response data
      if (data.success) {
        // Show the plot form and update available columns
        document.getElementById("plot-form").style.display = "block";

        // Update X-Axis and Y-Axis options with data from the selected table
        updatePlotOptions(data.x_axis_options, data.y_axis_options);
      } else {
        alert(data.message);
      }
    } catch (error) {
      console.error("Error:", error);
    }
  });

async function updatePlotOptions(xOptions, yOptions) {
  console.log("Updating plot options with:", xOptions, yOptions); // Debug log for options
  const xAxisSelect = document.querySelector('select[name="x_axis"]');
  const yAxisContainer = document.getElementById("y-axis-container"); // Correct targeting

  // Check if elements exist before modifying
  if (!xAxisSelect) {
    console.error("X-Axis select element not found");
    return;
  }
  if (!yAxisContainer) {
    console.error("Y-Axis container element not found");
    return;
  }

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

  // Debug log to ensure DOM elements were added correctly
  console.log("X-Axis options after update:", xAxisSelect.innerHTML);
  console.log("Y-Axis container after update:", yAxisContainer.innerHTML);
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
      showMessage("Please select an X-Axis value.", false, "plot-message-area");
      return;
    }

    // Get all selected table names
    const selectedTables = Array.from(
      document.getElementById("table-select").selectedOptions,
    ).map((option) => option.value);

    // Ensure at least one table is selected
    if (selectedTables.length > 0) {
      selectedTables.forEach((table) => formData.append("table_name[]", table));
    } else {
      showMessage(
        "Please select at least one table.",
        false,
        "plot-message-area",
      );
      return;
    }

    try {
      const response = await fetch("/plot", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.graph_json) {
        const plotData = JSON.parse(data.graph_json);
        Plotly.react("plot-container", plotData.data, plotData.layout);
        showMessage("Plot generated successfully.", true, "plot-message-area");
      } else if (data.error) {
        showMessage(data.error, false, "plot-message-area");
      } else {
        showMessage("An unknown error occurred.", false, "plot-message-area");
      }
    } catch (error) {
      console.error("Error:", error);
      showMessage("Error generating plot.", false, "plot-message-area");
    }
  });

// Open and close modal functionality
document
  .getElementById("add-column-btn")
  .addEventListener("click", function () {
    document.getElementById("add-column-modal").style.display = "block";
  });

document.getElementById("close-modal").addEventListener("click", function () {
  document.getElementById("add-column-modal").style.display = "none";
});

// Handle Add Column form submission asynchronously
// Handle Add Column form submission asynchronously
document
  .getElementById("add-column-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const tableName = document.getElementById("table-select").value;
    formData.append("table_name", tableName);

    fetch("/add-column", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        showMessage(data.message, data.success, "add-column-message-area");
        if (data.success) {
          // Optionally refresh columns
          // Hide modal if desired
          // document.getElementById("add-column-modal").style.display = "none";
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showMessage(
          "An error occurred while adding the column.",
          false,
          "add-column-message-area",
        );
      });
  });

function hideForms() {
  document.getElementById("spreadsheet-selection").style.display = "none";
  document.getElementById("instance-selection").style.display = "none";
}

window.onload = hideForms;

document.getElementById("form-select").addEventListener("change", function () {
  hideForms();

  var selectedForm = this.value;

  if (selectedForm === "table") {
    document.getElementById("spreadsheet-selection").style.display = "block";
  } else if (selectedForm === "instance") {
    document.getElementById("instance-selection").style.display = "block";
  }
});

function toggleValueChecklist(checkbox) {
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

function refreshTableList() {
  fetch("/get-tables")
    .then((response) => response.json())
    .then((data) => {
      const tableSelect = document.getElementById("table-select");
      tableSelect.innerHTML = ""; // Clear existing options
      data.tables.forEach((table) => {
        const option = document.createElement("option");
        option.value = table;
        option.textContent = table;
        tableSelect.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error fetching table list:", error);
    });
}

// Handle the upload form submission
document
  .getElementById("upload-form")
  .addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent the default form submission

    const form = event.target;
    const formData = new FormData(form);

    fetch("/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Display success message
          alert(data.message);
          // Refresh the table list
          refreshTableList();
        } else {
          // Display error message
          alert(data.message);
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while uploading the file.");
      });
  });

// Clear message when the upload form is changed
document.getElementById("upload-form").addEventListener("change", function () {
  showMessage("", true, "message-area"); // Clear the message area
});

// Clear plot messages when the plot form is changed
document.getElementById("plot-form").addEventListener("change", function () {
  showMessage("", true, "plot-message-area"); // Clear the plot message area
});
