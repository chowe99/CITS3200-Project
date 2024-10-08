let selectedTableName = ""; // Variable to store the selected table name

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
    const x_axis_value = document.querySelector('select[name="x_axis"]').value; // Get the selected x-axis value

    // Ensure x_axis value is not empty before appending
    if (x_axis_value) {
      formData.append("x_axis", x_axis_value); // Ensure x_axis is added
    } else {
      console.error("X-Axis value is missing");
      alert("Please select an X-Axis value.");
      return;
    }

    // Get all selected table names (since multiple selection is allowed)
    const selectedTables = Array.from(
      document.getElementById("table-select").selectedOptions,
    ).map((option) => option.value);

    // Ensure at least one table is selected before appending
    if (selectedTables.length > 0) {
      selectedTables.forEach((table) => formData.append("table_name[]", table)); // Append all selected table names
    } else {
      console.error("No tables selected");
      alert("Please select at least one table.");
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
      } else {
        alert(data.error);
      }
    } catch (error) {
      console.error("Error:", error);
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
        alert(data.message);
        if (data.success) {
          document.getElementById("add-column-modal").style.display = "none";
          // Optionally refresh column checkboxes without full page reload
          // or dynamically update the column list if possible
        }
      })
      .catch((error) => console.error("Error:", error));
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
