let isDragging = false;
let checkboxes = [];

function toggleDropdown(dropdownId) {
    document.getElementById(dropdownId).classList.toggle("show");
}

window.onclick = function(event) {
    if (!event.target.matches('.dropdown button')) {
        var dropdowns = document.getElementsByClassName("dropdown-content");
        for (var i = 0; i < dropdowns.length; i++) {
            var openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}

function toggleFullScreen() {
    const plotContainer = document.getElementById('plot-container');
    plotContainer.classList.toggle('fullscreen');
}

function toggleCheckbox(event) {
    const checkbox = event.target;
    checkbox.checked = !checkbox.checked;
}

function startDrag(event) {
    event.preventDefault();
    isDragging = true;

    // Store checkboxes
    checkboxes = Array.from(document.querySelectorAll('.checkbox-group input[type="checkbox"]'));

    // Add event listeners for mousemove and mouseup
    document.addEventListener('mousemove', drag);
    document.addEventListener('mouseup', endDrag);
}

function drag(event) {
    if (!isDragging) return;

    // Calculate which checkboxes to select
    checkboxes.forEach(checkbox => {
        const box = checkbox.getBoundingClientRect();
        const isWithin = (
            event.clientX >= box.left &&
            event.clientX <= box.right &&
            event.clientY >= box.top &&
            event.clientY <= box.bottom
        );
        checkbox.checked = isWithin;
    });
}

function endDrag() {
    isDragging = false;
    document.removeEventListener('mousemove', drag);
    document.removeEventListener('mouseup', endDrag);
}

// Optional: Click event to ensure drag selection works even when clicking directly on checkboxes
document.querySelectorAll('.checkbox-group input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('mousedown', function(event) {
        if (isDragging) {
            event.preventDefault(); // Prevent checkbox toggle
        }
    });
});





// Function to toggle full screen for the plot container
function toggleFullScreen() {
    const plotContainer = document.getElementById('plot-container');

    if (!document.fullscreenElement) {
        // If not in full screen, request to enter full screen
        plotContainer.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
        });
    } else {
        // If already in full screen, exit full screen
        document.exitFullscreen();
    }
}

// Function to handle resizing of the plot
function resizePlot() {
    const plotContainer = document.getElementById('plot-container');
    Plotly.Plots.resize(plotContainer);
}

// Listen for fullscreen change event
document.addEventListener('fullscreenchange', resizePlot);
document.addEventListener('webkitfullscreenchange', resizePlot);
document.addEventListener('mozfullscreenchange', resizePlot);
document.addEventListener('MSFullscreenChange', resizePlot);


// Function to show messages
async function showMessage(message, isSuccess, elementId) {
  const messageArea = document.getElementById(elementId);
  if (messageArea) {
    messageArea.textContent = message;
    messageArea.style.color = isSuccess ? "green" : "red";
    messageArea.style.display = message ? "block" : "none"; // Hide if message is empty
  }
}

// Update the upload form submission handler to fetch instances after successful upload
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
        // Refresh the table and instance lists
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

// Function to fetch and display instances
async function fetchAndDisplayInstances() {
  try {
    const response = await fetch("/get-instances");
    const data = await response.json();
    const instanceSelection = document.getElementById("instance-selection");
    instanceSelection.innerHTML = ""; // Clear existing options

    if (data.instances && Object.keys(data.instances).length > 0) {
      const label = document.createElement("label");
      label.setAttribute("for", "instance-select");
      label.textContent = "Select instance(s):";
      instanceSelection.appendChild(label);

      for (const [instanceName, values] of Object.entries(data.instances)) {
        const div = document.createElement("div");

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = instanceName;
        checkbox.name = "instance_names";
        checkbox.value = instanceName;
        checkbox.onclick = function () {
          toggleValueChecklist(this);
        };

        const label = document.createElement("label");
        label.setAttribute("for", instanceName);
        label.textContent = instanceName;

        div.appendChild(checkbox);
        div.appendChild(label);

        const checklist = document.createElement("div");
        checklist.className = "value-checklist";
        checklist.style.display = "none";

        values.forEach((value) => {
          const valueCheckbox = document.createElement("input");
          valueCheckbox.type = "checkbox";
          valueCheckbox.id = `${instanceName}_${value}`;
          valueCheckbox.name = `${instanceName}_values`;
          valueCheckbox.value = value;

          const valueLabel = document.createElement("label");
          valueLabel.setAttribute("for", `${instanceName}_${value}`);
          valueLabel.textContent = value;

          checklist.appendChild(valueCheckbox);
          checklist.appendChild(valueLabel);
          checklist.appendChild(document.createElement("br"));
        });

        div.appendChild(checklist);
        instanceSelection.appendChild(div);
      }
    } else {
      const noInstancesMsg = document.createElement("p");
      noInstancesMsg.textContent = "No instances available.";
      instanceSelection.appendChild(noInstancesMsg);
    }
  } catch (error) {
    console.error("Error fetching instances:", error);
    await showMessage("Error fetching instance list.", false, "message-area");
  }
}

// Modify refreshTableList to also fetch instances
async function refreshTableList() {
  try {
    const [tablesResponse, instancesResponse] = await Promise.all([
      fetch("/get-tables"),
      fetch("/get-instances"),
    ]);

    const tablesData = await tablesResponse.json();
    const instancesData = await instancesResponse.json();

    const tableCheckboxes = document.getElementById("table-checkboxes");
    tableCheckboxes.innerHTML = ""; // Clear existing options
    tablesData.tables.forEach((table) => {
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

    // Now, fetch and display instances
    await fetchAndDisplayInstances();
  } catch (error) {
    console.error("Error refreshing table and instance lists:", error);
    await showMessage(
      "Error refreshing table and instance lists.",
      false,
      "message-area",
    );
  }
}
// Handle the filter form submission
document
  .getElementById("filter-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    console.log("Filter form submitted.");

    const formData = new FormData(event.target);

    // Collect selected tables
    const selectedTables = Array.from(
      document.querySelectorAll('input[name="table_name[]"]:checked'),
    ).map((checkbox) => checkbox.value);
    console.log("Selected Tables:", selectedTables);

    // Collect selected instances and their values
    const instances = [];
    document
      .querySelectorAll('input[name="instance_names"]:checked')
      .forEach((checkbox) => {
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
    console.log("Collected Instances:", instances);

    // Collect x_axis value
    const x_axis_value = document.querySelector('select[name="x_axis"]').value;

    // Collect selected y_axis values
    const y_axis_values = Array.from(
      document.querySelectorAll('input[name="y_axis"]:checked'),
    ).map((checkbox) => checkbox.value);

    console.log("X Axis:", x_axis_value);
    console.log("Y Axis:", y_axis_values);

    // Ensure x_axis and y_axis are selected
    if (!x_axis_value) {
      await showMessage(
        "Please select an X-Axis value.",
        false,
        "plot-message-area",
      );
      return;
    }

    if (y_axis_values.length === 0) {
      await showMessage(
        "Please select at least one Y-Axis value.",
        false,
        "plot-message-area",
      );
      return;
    }

    // Include selected tables and instances in form data
    selectedTables.forEach((table) => formData.append("table_name[]", table));
    formData.append("instances_json", JSON.stringify(instances));

    // Include x_axis and y_axis in form data
    formData.append("x_axis", x_axis_value);
    y_axis_values.forEach((y_axis) => formData.append("y_axis", y_axis));

    // Decryption password
    const decryptPassword = document.getElementById("decrypt_password").value;
    formData.append("decrypt_password", decryptPassword);

    try {
      const response = await fetch("/plot", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      console.log("Response from /plot:", data);
      if (data.graph_json) {
        const plotData = JSON.parse(data.graph_json);
        Plotly.react("plot-container", plotData.data, plotData.layout);

        await showMessage(
          message,
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
      await showMessage(
        "An error occurred while generating the plot.",
        false,
        "plot-message-area",
      );
    }
  });

// Function to toggle visibility of instance value checklists
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

// Clear messages when forms are changed
document
  .getElementById("upload-form")
  .addEventListener("change", async function () {
    await showMessage("", true, "message-area"); // Clear the message area
  });

document
  .getElementById("filter-form")
  .addEventListener("change", async function () {
    await showMessage("", true, "plot-message-area"); // Clear the plot message area
  });
