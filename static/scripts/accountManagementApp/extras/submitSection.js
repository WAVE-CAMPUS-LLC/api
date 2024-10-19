document.getElementById('profilePreferencesForm').addEventListener('submit', function (event) {
    event.preventDefault(); // Prevent default form submission

    const formData = new FormData(this); // Create FormData object

    // Collect values from checkboxes/radio buttons and add them to FormData
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
    checkboxes.forEach((checkbox) => {
        formData.append(checkbox.name, checkbox.value);
    });

    const radios = document.querySelectorAll('input[type="radio"]:checked');
    radios.forEach((radio) => {
        formData.append(radio.name, radio.value);
    });

    fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': '{{ csrf_token }}' // Ensure the CSRF token is correct
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json(); // Parse JSON response
    })
    .then(data => {
        if (data.success) {
            console.log(data.message); // Handle success
            // Optionally: redirect or update the UI
        } else {
            console.error('Form submission failed:', data.errors); // Handle validation errors
            // Display errors in the UI
            Object.keys(data.errors).forEach(field => {
                // You could show the errors in a specific location in your form
                console.error(`${field}: ${data.errors[field].join(', ')}`);
            });
        }
    })
    .catch(error => {
        console.error('There was a problem with the fetch operation:', error); // Handle fetch errors
    });
});
