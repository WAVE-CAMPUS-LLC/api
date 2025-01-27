// Retrieve the Stripe key from the hidden input field
const stripeKey = document.getElementById("stripeKey").value;
var stripe = Stripe(stripeKey);

const elements = stripe.elements();
const cardElement = elements.create("card");
cardElement.mount("#card-element");

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

const form = document.getElementById("addCardModalForm");
const cardUrl = document.getElementById("addCardUrl").value;
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const { token, error } = await stripe.createToken(cardElement);

    if (error) {
        console.error("Error creating token: ", error.message);
        return;
    }

    const response = await fetch(cardUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ token: token.id }),
    });

    const data = await response.json();

    if (data.success) {
        location.reload(); // Refresh the page to show the updated messages
    } else {
        console.error("Failed to add card. Check server messages.");
        location.reload(); // Refresh to display error messages from the backend
    }
});