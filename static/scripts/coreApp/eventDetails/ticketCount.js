document.addEventListener('DOMContentLoaded', function () {
    let cart = {};

    // Function to update the cart display
    function updateCartDisplay() {
        const emptyCart = document.getElementById("emptyCart");
        const cartItemsContainer = document.getElementById("cartItems");
        const cartItemContainer = document.getElementById("cartItemContainer");
        const checkoutTotalElement = document.getElementById("checkoutTotal");
        const checkoutRow = document.getElementById("checkoutRow");

        // Clear the current items inside the cart container
        cartItemContainer.innerHTML = "";

        let totalAmount = 0; // Variable to store the total amount for checkout

        // Check if the cart is empty
        if (Object.keys(cart).length === 0) {
            // Show the empty cart message and hide cart items
            emptyCart.style.display = "block";
            cartItemsContainer.style.display = "none";
            checkoutRow.style.display = "none";
        } else {
            // Hide the empty cart message and show the cart items
            emptyCart.style.display = "none";
            cartItemsContainer.style.display = "block";
            checkoutRow.style.display = "block";

            // Loop through each item in the cart to populate cart items and total
            for (let ticketId in cart) {
                const ticket = cart[ticketId];
                const ticketTotalPrice = ticket.price * ticket.quantity;
                totalAmount += ticketTotalPrice;

                // Create a div element for each cart item
                const cartItem = document.createElement("div");
                cartItem.classList.add("cartItem");

                // Add ticket information to the cart item element
                cartItem.innerHTML = `
                    <span class="cartItemName">${ticket.name}</span>
                    <div class="priceQuantity">
                        <span class="cartItemCount">x<span>${ticket.quantity}</span></span>
                        <span class="cartItemPrice"> $${ticketTotalPrice.toFixed(2)}</span>
                    </div>
                `;

                // Append the cart item to the cartItemContainer
                cartItemContainer.appendChild(cartItem);
            }

            // Update the checkout total amount and display it
            checkoutTotalElement.textContent = `$${totalAmount.toFixed(2)}`;
            console.log("Total Amount:", totalAmount);
        }
    }

    // Function to add a ticket to the cart
    function addTicket(ticketId, ticketName, ticketPrice) {
        if (!cart[ticketId]) {
            cart[ticketId] = { name: ticketName, price: ticketPrice, quantity: 1 };
        } else {
            cart[ticketId].quantity += 1;
        }
        updateCartDisplay();
    }

    // Function to remove a ticket from the cart
    function removeTicket(ticketId) {
        if (cart[ticketId]) {
            cart[ticketId].quantity -= 1;
            if (cart[ticketId].quantity <= 0) {
                delete cart[ticketId];
            }
        }
        updateCartDisplay();
    }

    // Function to handle checkout
    function handleCheckout() {
        // Prepare data to send to the server
        const checkoutData = {
            cart: cart,
            total: calculateTotal(), // Calculate the total amount
        };

        // Send the data to the server using fetch
        fetch('/checkout/', { // Replace with your actual checkout URL
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(), // Include CSRF token for security
            },
            body: JSON.stringify(checkoutData),
        })
            .then(response => response.json())
            .then(data => {
                // Handle the response from the server
                if (data.success) {
                    // Redirect to the payment page or show success message
                    window.location.href = data.redirect_url; // Redirect to the payment page
                } else {
                    // Handle errors
                    alert(data.message || 'An error occurred. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            });
    }

    // Function to calculate total amount
    function calculateTotal() {
        let totalAmount = 0;
        for (let ticketId in cart) {
            const ticket = cart[ticketId];
            totalAmount += ticket.price * ticket.quantity;
        }
        return totalAmount;
    }

    // Function to get CSRF token from the cookie
    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    // Event listeners for the Add and Remove buttons
    document.querySelectorAll(".addTicket").forEach(button => {
        button.addEventListener("click", function () {
            const ticketId = this.getAttribute("data-ticket-id");
            const ticketName = this.getAttribute("data-ticket-name");
            const ticketPrice = parseFloat(this.getAttribute("data-ticket-price"));
            addTicket(ticketId, ticketName, ticketPrice);
        });
    });

    document.querySelectorAll(".removeTicket").forEach(button => {
        button.addEventListener("click", function () {
            const ticketId = this.getAttribute("data-ticket-id");
            removeTicket(ticketId);
        });
    });

    // Add an event listener for the checkout button
    document.getElementById("checkoutButton").addEventListener("click", handleCheckout);

    // Initial call to set up the cart display
    updateCartDisplay();
});
