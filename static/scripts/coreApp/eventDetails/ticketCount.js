document.addEventListener("DOMContentLoaded", function () {
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
                        <span class="cartItemCount">x<span>${
                          ticket.quantity
                        }</span></span>
                        <span class="cartItemPrice"> $${ticketTotalPrice.toFixed(
                          2
                        )}</span>
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
  const saveUrl = document.getElementById("save-url").value;

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        // Check if this cookie string begins with the name we want
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function saveCartToServer() {
    fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(cart),
    }).catch((error) => console.error("Error saving cart:", error));
  }

  // Function to update the displayed quantity for a ticket in the UI
  function updateTicketAmountDisplay(ticketId) {
    const ticketAmountSpan = document.querySelector(
      `.currentTicketAmount[data-ticket-id="${ticketId}"]`
    );
    if (ticketAmountSpan) {
      ticketAmountSpan.textContent = cart[ticketId]
        ? cart[ticketId].quantity
        : 0;
    }
  }

  // Function to add a ticket to the cart
  function addTicket(
    ticketId,
    ticketName,
    ticketPrice,
    stripePriceId,
    stripeProductId,
    eventId,
    eventName
  ) {
    if (!cart[ticketId]) {
      cart[ticketId] = {
        name: ticketName,
        price: ticketPrice,
        quantity: 1,
        priceId: stripePriceId,
        productId: stripeProductId,
        eventId: eventId,
        eventTitle: eventName,
      };
    } else {
      cart[ticketId].quantity += 1;
    }
    updateCartDisplay();
    updateTicketAmountDisplay(ticketId);
    saveCartToServer();
  }

  function returnCheckout() {
    const checkoutUrl = document.getElementById("checkout-url").value;
    fetch(checkoutUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(cart),
    })
      .then((response) => {
        if (!response.ok) {
          // Log response if it's not ok
          console.error("Error response:", response);
          return response.json(); // Still attempt to parse JSON
        }
        return response.json();
      })
      .then((data) => {
        if (data.url) {
          window.location.href = data.url;
        } else {
          console.error("Error fetching checkout URL:", data);
        }
      })
      .catch((error) => console.error("Error fetching checkout URL:", error));
  }

  const checkoutButton = document.getElementById("checkoutButton");
  checkoutButton.addEventListener("click", returnCheckout);

  function getCSRFToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]").value;
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
    updateTicketAmountDisplay(ticketId);
    saveCartToServer();
  }

  // Event listeners for the Add and Remove buttons
  document.querySelectorAll(".addTicket").forEach((button) => {
    button.addEventListener("click", function () {
      const ticketId = this.getAttribute("data-ticket-id");
      const ticketName = this.getAttribute("data-ticket-name");
      const ticketPrice = parseFloat(this.getAttribute("data-ticket-price"));
      const stripePriceId = this.getAttribute("data-stripe-price-id");
      const stripeProductId = this.getAttribute("data-stripe-product-id");
      const eventId = this.getAttribute("data-ticket-event-id");
      const eventName = this.getAttribute("data-ticket-event-name");
      addTicket(
        ticketId,
        ticketName,
        ticketPrice,
        stripePriceId,
        stripeProductId,
        eventId,
        eventName
      );
    });
  });

  document.querySelectorAll(".removeTicket").forEach((button) => {
    button.addEventListener("click", function () {
      const ticketId = this.getAttribute("data-ticket-id");
      removeTicket(ticketId);
    });
  });

  // Initial call to set up the cart display
  updateCartDisplay();
});
