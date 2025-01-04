
document.querySelectorAll(".category-event-card").forEach((card) => {
    card.addEventListener("click", (e) => {
        const eventId = card.dataset.eventId;

        // Capture guest ID from local storage or generate a new one
        let guestId = localStorage.getItem("guestId");
        if (!guestId) {
            guestId = self.crypto.randomUUID();
            localStorage.setItem("guestId", guestId);
        }

        const eventClickURL = document.getElementById("eventClickURL").value;
        // Send data to the server
        fetch(eventClickURL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"), // Include CSRF token
            },
            body: JSON.stringify({
                eventId: eventId,
                guestId: guestId,
                interaction_type: "Clicked",
            }),
        })
            .then((response) => response.json())
            .then((data) => console.log("Interaction logged:", data))
            .catch((error) => console.error("Error logging interaction:", error));
    });
});

// Utility function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";").map((c) => c.trim());
        cookies.forEach((cookie) => {
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.split("=")[1]);
            }
        });
    }
    return cookieValue;
}
