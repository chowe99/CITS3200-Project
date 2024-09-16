// JavaScript to handle plot form submission and update the plot dynamically
document.getElementById('plot-form').addEventListener('submit', function (event) {
    event.preventDefault(); // Prevent the default form submission

    // Create a FormData object to send form data via AJAX
    const formData = new FormData(event.target);

    // Use Fetch API to send a POST request to the /plot endpoint
    fetch('/plot', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json()) // Expect a JSON response from the server
        .then(data => {
            if (data.plot_url) {
                // Update the plot image with the new plot URL
                const plotImage = document.getElementById('plot-image');
                plotImage.src = data.plot_url;
                plotImage.style.display = 'block';
            } else if (data.error) {
                alert(data.error); // Show error if units are incompatible
            }
        })
        .catch(error => console.error('Error:', error));
});

// Open and close modal functionality
document.getElementById('add-column-btn').addEventListener('click', function () {
    document.getElementById('add-column-modal').style.display = 'block';
});

document.getElementById('close-modal').addEventListener('click', function () {
    document.getElementById('add-column-modal').style.display = 'none';
});

// Handle Add Column form submission asynchronously
document.getElementById('add-column-form').addEventListener('submit', function (event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    fetch('/add-column', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            if (data.success) {
                document.getElementById('add-column-modal').style.display = 'none';
                // Optionally refresh column checkboxes without full page reload
                // or dynamically update the column list if possible
            }
        })
        .catch(error => console.error('Error:', error));
});

