document.addEventListener("DOMContentLoaded", function () {
    const rsvpForm = document.getElementById("rsvpForm");
    const submitButton = document.getElementById("submitBtn");

    rsvpForm?.addEventListener("submit", function (e) {
        e.preventDefault();
        submitButton.disabled = true;
        submitButton.style.opacity = 0.5;

        const formData = new FormData(rsvpForm);

        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch(rsvpForm.action, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errData => { throw errData; });
            }
            return response.json();
        })
        .then(data => {
                window.location.reload();
        })
        .catch(errorData => {
            console.error("RSVP error:", errorData);
            window.location.reload();
        });
    });
});
