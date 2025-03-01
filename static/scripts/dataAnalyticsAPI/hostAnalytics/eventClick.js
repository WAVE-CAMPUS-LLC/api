function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Check if this cookie string begins with the name we want
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

function handleEventClick(event, eventId) {
    event.preventDefault(); // Stop the link navigation
    trackEventClick(eventId); // Call the tracking function
    setTimeout(() => {
        window.location.href = event.target.closest('a').href; // Navigate after tracking
    }, 200); // Adjust delay if necessary
}


function trackEventClick(eventId) {

    const fetchUrl = document.getElementById('trackEventClickURL').value;

    fetch(fetchUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrfmiddlewaretoken'),
        },
        body: JSON.stringify({
            event_id: eventId,
            interaction_type: 'Clicked',
        }),
    })
        .then(response => {
            if (!response.ok) {
                console.error('Fetch failed:', response.statusText);
            }
            return response.json();
        })
        .then(data => {
        })
        .catch(error => console.error('Error during fetch:', error));
}



// Add this line to ensure the function is available globally
window.trackEventClick = trackEventClick;
