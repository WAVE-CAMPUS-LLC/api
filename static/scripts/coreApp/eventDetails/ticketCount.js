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
    // Replace with the URL mapped to your create_checkout_session view.
    const checkoutSessionUrl = document.getElementById("hostedCheckout").value;
        
    fetch(checkoutSessionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      // Optionally send additional data if needed:
      body: JSON.stringify({ /* you can include extra details if required */ }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.sessionUrl) {
          // Redirect the user to Stripe's hosted checkout page.
          window.location.href = data.sessionUrl;
        } else {
          console.error("Error creating checkout session:", data.error);
        }
      })
      .catch(error => console.error("Error:", error));
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
  function addCrewTicketToCart({
    ticketId,
    ticketName,
    ticketPrice,
    crewId,
    crewName,
    crewSize,
    eventId,
  }) {
    // Generate a unique cart key (e.g., "TICKETID_crew_CREWID")
    const cartKey = `${ticketId}_crew_${crewId}`;

    // Check if this crew ticket already exists in the cart
    if (!cart[cartKey]) {
      cart[cartKey] = {
        name: `${ticketName} (${crewName} Crew)`,
        price: ticketPrice,
        quantity: crewSize,
        ticketId: ticketId,
        crewId: crewId,
        eventId: eventId,
      };
    } else {
      // If the user picks the same crew ticket again,
      // just add more quantity. Usually you'd add `crewSize`,
      // but you can decide whether to let them add it multiple times.
      cart[cartKey].quantity += crewSize;
    }
    // Update display and save
    updateCartDisplay();
    saveCartToServer();

    // Disable the button after adding the crew ticket to the cart
    const button = document.querySelector(
      `.crewCheckoutButton[data-ticket-id="${ticketId}"][data-crew-id="${crewId}"]`
    );
    if (button) {
      button.disabled = true;
      button.textContent = "Added to Cart";
    }
  }

  //------------------------------------------------------------------
  // NEW: Add event listeners for crew checkout buttons
  //------------------------------------------------------------------
  const crewCheckoutButtons = document.querySelectorAll(".crewCheckoutButton");
  crewCheckoutButtons.forEach((btn) => {
    btn.addEventListener("click", (event) => {
      // Prevent any form submission
      event.preventDefault();

      // Read data attributes from button
      const ticketId = btn.getAttribute("data-ticket-id");
      const ticketName = btn.getAttribute("data-ticket-name");
      const ticketPrice = parseFloat(btn.getAttribute("data-ticket-price"));
      const crewId = btn.getAttribute("data-crew-id");
      const crewName = btn.getAttribute("data-crew-name");
      const crewSize = parseInt(btn.getAttribute("data-crew-size"), 10);
      const eventId = btn.getAttribute("data-ticket-event-id");

      // Add this crew-based ticket to the cart
      addCrewTicketToCart({
        ticketId,
        ticketName,
        ticketPrice,
        crewId,
        crewName,
        crewSize,
        eventId,
      });

      // Optional: close the crew popup or do any UI cleanup you need
      const modalId = `chooseCrewPopup${ticketId}`;
      const modal = document.getElementById(modalId);
      if (modal) {
        modal.classList.add("hidden");
      }
    });
  });

  // Initial call to set up the cart display
  updateCartDisplay();
});
