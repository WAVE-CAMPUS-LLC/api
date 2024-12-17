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
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const { token, error } = await stripe.createToken(cardElement, {
        name: document.getElementById("cardName").value,
        currency: "usd",
    });

    if (error) {
        console.error(error);
        return;
    } else {
        const cardUrl = document.getElementById("addCardUrl").value;
        fetch(cardUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                token: token.id,
            }),
        })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Failed to add card");
            }
            return response.json();
        })
        .then((data) => {
            if (data.success) {
                alert("Card added successfully");
            } else {
                alert("Failed to add card: " + data.message);
            }
        })
        .catch((error) => {
            console.error("Error:", error);
        });
    }

});