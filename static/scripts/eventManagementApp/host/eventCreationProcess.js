$(document).ready(function () {
    let currentSectionIndex = 0; // Start with the first section
    const sections = $('section#stage-section'); // Select all section elements

    const saveUrl = document.getElementById('creation-control').dataset.saveUrl;

    // Function to display the current section and hide others
    function displaySection(index) {
        sections.hide(); // Hide all sections
        $(sections[index]).show(); // Show the current section
    }

    // Initial display
    displaySection(currentSectionIndex);

    // Function to get CSRF token for AJAX requests
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Check if this cookie string begins with the name we want
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Function to update visibility based on privacy selection
    function updateVisibility() {
        const selectedPrivacy = $('#privacy').val();
        if (selectedPrivacy === 'organization') {
            $('#discoverability_level').closest('.form-group').hide(); // Hide discoverability if organization is selected
        } else {
            $('#discoverability_level').closest('.form-group').show(); // Show otherwise
        }
    }

    // Initial setup for discoverability level visibility
    updateVisibility();

    // Listen for changes on the privacy select
    $('#privacy').change(function () {
        updateVisibility(); // Update visibility on change
    });

    // Handle click on the "Next" button
    $('#next-sectionbtn').click(function () {
        // Collect the form data
        saveFormData()
    });

    // Handle click on the "Previous" button
    $('#previous-sectionbtn').click(function () {
        saveFormData(function () {
            if (currentSectionIndex > 0) {
                currentSectionIndex--; // Decrement the section index
                displaySection(currentSectionIndex); // Display the previous section
            }
        });
    });

    function saveFormData(callback) {
        const formData = new FormData(document.getElementById('eventForm'));
        formData.append('event_id', '{{ event.eventId }}');  // Add the event ID to the form data

        // AJAX request to save progress
        $.ajax({
            url: saveUrl,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')  // CSRF token for protection
            },
            success: function (response) {
                if (callback) {
                    callback();
                } else {
                    // Move to the next section if no callback
                    if (currentSectionIndex < sections.length - 1) {
                        currentSectionIndex++; // Increment the section index
                        displaySection(currentSectionIndex); // Display the next section
                    }
                }
            },
            error: function (xhr, status, error) {
                console.error('Failed to save progress', xhr.responseJSON);
                // Optionally, handle errors (e.g., show a message to the user)
            }
        });
    }
});
