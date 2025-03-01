document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById("forgotCardForm");
    const csrfToken = document.getElementById("csrf_token").value;

    form.addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent the default form submission
        const formData = new FormData(form); // Get form data
        
        // Send POST request to Django view
        fetch(form.action, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken
            },
            body: formData
        })
        .then(response => {
            if (response.ok) {
                document.getElementById("forgotCardForm").style.display = "none";
                document.getElementById("notificationCardExists").style.display = "block";
            } else {
                document.getElementById("notificationCardDNE").style.display = "block";
            }
        })
        .catch(error => {
        })
    });
});
