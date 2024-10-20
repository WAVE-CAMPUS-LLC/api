document.addEventListener('DOMContentLoaded', function () {
    const checkbox = document.getElementById('displayOnCollegeCheckbox');
    const form = document.getElementById('college-display-form');

    checkbox.addEventListener('change', function () {
        // Create a hidden input to send the false value
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = 'displayOnCollege';
        hiddenInput.value = checkbox.checked ? 'True' : 'False'; // Set value based on checkbox state

        // Clear any previous hidden inputs
        const existingInput = form.querySelector('input[name="displayOnCollege"]');
        if (existingInput) {
            existingInput.remove();
        }

        // Append the hidden input
        form.appendChild(hiddenInput);

        // Submit the form when the checkbox state changes
        form.submit();
    });
});