document.addEventListener("DOMContentLoaded", function () {
  // Cart related variables
  let cart = {};
  let discount_percentage;
  const saveUrl = document.getElementById("save-url").value;

  // Coupon related elements
  const couponCodeButton = document.getElementById("couponCodeButton");
  const couponCodeInput = document.getElementById("couponCodeInput");
  let couponMessage = document.getElementById("couponMessage");
  let couponCodeError = document.getElementById("couponCodeError");
  const eventIdElement = document.getElementById("event-id");
  
  // Clear cart and coupon code when the page loads
  clearCartAndCoupon();
  
  // Add event listener to clear cart when the user leaves the page
  window.addEventListener("beforeunload", function() {
    clearCartAndCoupon();
  });
  
  // Add event listeners to all links on the page
  document.addEventListener('click', function(event) {
    // Check if the clicked element is a link or inside a link
    const link = event.target.closest('a');
    if (link && !link.hasAttribute('data-no-clear-cart')) {
      // Only clear cart for links that navigate away from the page
      // Skip links that open in a new tab/window
      if (!link.target || link.target.toLowerCase() !== '_blank') {
        // Clear the cart before navigation
        clearCartAndCoupon();
      }
    }
  });
  
  // Early return if coupon elements don't exist
  if (couponCodeButton && eventIdElement) {
    setupCouponElements();
    setupCouponHandlers();
  }

  // Function to clear cart and coupon code
  function clearCartAndCoupon() {
    // Clear the cart in localStorage
    localStorage.removeItem('cart');
    
    // Initialize an empty cart object
    cart = {};
    
    // Reset all price elements to their original values
    document.querySelectorAll('.ticket-price').forEach(element => {
      const originalPrice = element.getAttribute('data-original-price');
      if (originalPrice) {
        element.textContent = '$' + parseFloat(originalPrice).toFixed(2);
        element.removeAttribute('data-original-price');
      }
    });
    
    // Reset the checkout total if it exists
    const checkoutTotalElement = document.getElementById("checkoutTotal");
    if (checkoutTotalElement) {
      checkoutTotalElement.textContent = "$0.00";
      checkoutTotalElement.removeAttribute('data-original-total');
      checkoutTotalElement.removeAttribute('data-current-total');
    }
    
    // Update the cart display
    updateCartDisplay();
    
    // Reset all ticket counters to 0
    document.querySelectorAll('.currentTicketAmount').forEach(counter => {
      counter.textContent = '0';
    });
    
    // Reset coupon UI if elements exist
    if (couponCodeInput && couponCodeButton && document.getElementById("removeCouponButton")) {
      couponCodeInput.disabled = false;
      couponCodeInput.classList.remove("bg-gray-100");
      couponCodeInput.value = "";
      
      // Show the Apply button container and hide the Remove button container
      document.getElementById("applyButtonContainer").classList.remove("hidden");
      document.getElementById("removeCouponButtonContainer").classList.add("hidden");
      
      // Reset the Apply button
      couponCodeButton.textContent = "Apply";
      couponCodeButton.disabled = false;
      couponCodeButton.style.opacity = 1;
      
      const removeCouponButton = document.getElementById("removeCouponButton");
      removeCouponButton.classList.add("hidden");
      
      if (couponMessage) {
        couponMessage.textContent = "";
        couponMessage.classList.add("hidden");
      }
    }
    
    // Also clear the cart on the server
    fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({}),
    })
    .then(response => {
      if (!response.ok) {
        console.error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log("Cart cleared successfully on server:", data);
    })
    .catch((error) => {
      console.error("Error clearing cart on server:", error);
    });
  }

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
    let hasTickets = false; // Flag to check if there are actual tickets in the cart

    // Check if the cart is empty of tickets
    for (let ticketId in cart) {
      // Skip non-ticket properties
      if (ticketId === 'coupon_code' || ticketId === 'discount_percentage') {
        continue;
      }
      hasTickets = true;
      break;
    }

    if (!hasTickets) {
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
        // Skip non-ticket properties
        if (ticketId === 'coupon_code' || ticketId === 'discount_percentage') {
          continue;
        }
        
        const ticket = cart[ticketId];
        // Ensure price and quantity are valid numbers
        const price = parseFloat(ticket.price) || 0;
        const quantity = parseInt(ticket.quantity) || 0;
        const ticketTotalPrice = price * quantity;
        totalAmount += ticketTotalPrice;

        // Create a div element for each cart item
        const cartItem = document.createElement("div");
        cartItem.classList.add("cartItem");

        // Add ticket information to the cart item element
        cartItem.innerHTML = `
                    <span class="cartItemName">${ticket.name}</span>
                    <div class="priceQuantity">
                        <span class="cartItemCount">x<span>${quantity}</span></span>
                        <span class="cartItemPrice"> $${ticketTotalPrice.toFixed(2)}</span>
                    </div>
                `;

        // Append the cart item to the cartItemContainer
        cartItemContainer.appendChild(cartItem);
      }

      // Update the checkout total amount and display it
      checkoutTotalElement.textContent = `$${totalAmount.toFixed(2)}`;
      
      // Store the current total for reference (without overriding any existing data-original-total)
      if (!checkoutTotalElement.hasAttribute('data-current-total')) {
        checkoutTotalElement.setAttribute('data-current-total', totalAmount.toFixed(2));
      } else {
        checkoutTotalElement.setAttribute('data-current-total', totalAmount.toFixed(2));
      }
    }
  }

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
    // Save cart to localStorage first
    localStorage.setItem("cart", JSON.stringify(cart));
    
    fetch(saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(cart),
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log("Cart saved successfully:", data);
    })
    .catch((error) => {
      console.error("Error saving cart:", error);
    });
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
    // Ensure all values are of the correct type
    const parsedTicketPrice = parseFloat(ticketPrice);
    
    if (isNaN(parsedTicketPrice) || parsedTicketPrice <= 0) {
      console.error("Invalid ticket price:", ticketPrice);
      return;
    }
    
    if (!ticketId || !ticketName || !eventId) {
      console.error("Missing required ticket information");
      return;
    }
    
    if (!cart[ticketId]) {
      cart[ticketId] = {
        name: String(ticketName),
        price: parsedTicketPrice,
        quantity: 1,
        priceId: stripePriceId ? String(stripePriceId) : "",
        productId: stripeProductId ? String(stripeProductId) : "",
        eventId: String(eventId),
        eventTitle: eventName ? String(eventName) : "",
      };
    } else {
      cart[ticketId].quantity += 1;
    }
    
    // Check if there's a coupon applied and recalculate the total
    if (cart.coupon_code && cart.discount_percentage) {
      // Apply the discount to the cart
      applyDiscountToCart(cart.discount_percentage);
    }
    
    updateCartDisplay();
    updateTicketAmountDisplay(ticketId);
    saveCartToServer();
  }

  function returnCheckout() {
    // Replace with the URL mapped to your create_checkout_session view.
    const checkoutSessionUrl = document.getElementById("hostedCheckout").value;
    
    // Get the cart from localStorage
    const cartFromStorage = JSON.parse(localStorage.getItem("cart") || "{}");
    
    // Create a clean cart object with only the necessary data
    const cart = {};
    
    // Don't send the request if the cart is empty
    if (Object.keys(cartFromStorage).length === 0) {
      alert("Your cart is empty. Please add tickets before checking out.");
      return;
    }
    
    // Check if a discount is applied
    const hasDiscount = 'discount_percentage' in cartFromStorage;
    const discountPercentage = hasDiscount ? parseFloat(cartFromStorage.discount_percentage) : 0;
    
    // Copy only valid ticket items to the cart
    for (const [key, value] of Object.entries(cartFromStorage)) {
      if (key === 'coupon_code') {
        cart[key] = value;
        continue;
      }
      
      if (key === 'discount_percentage') {
        cart[key] = value;
        continue;
      }
      
      // Ensure this is a valid ticket item
      if (typeof value === 'object' && value !== null && 
          'name' in value && 'price' in value && 'quantity' in value && 'eventId' in value) {
        // Ensure all values are of the correct type
        const ticketItem = {
          name: String(value.name),
          price: parseFloat(value.price),
          quantity: parseInt(value.quantity, 10),
          eventId: String(value.eventId)
        };
        
        // If there's an original price (before discount), include it
        if (value.originalPrice) {
          ticketItem.originalPrice = parseFloat(value.originalPrice);
        }
        
        // Only add items with valid values
        // For 100% discounts, allow zero-priced tickets
        if (!isNaN(ticketItem.price) && !isNaN(ticketItem.quantity) && ticketItem.quantity > 0 && 
            (ticketItem.price > 0 || (hasDiscount && discountPercentage >= 100))) {
          cart[key] = ticketItem;
        }
      }
    }
    
    // Check if we have any valid tickets after filtering
    const hasOnlyCouponInfo = (Object.keys(cart).length === 1 && 'coupon_code' in cart) || 
                             (Object.keys(cart).length === 1 && 'discount_percentage' in cart) ||
                             (Object.keys(cart).length === 2 && 'coupon_code' in cart && 'discount_percentage' in cart);
                             
    if (Object.keys(cart).length === 0 || hasOnlyCouponInfo) {
      alert("Your cart doesn't contain any valid tickets. Please add tickets before checking out.");
      return;
    }
    
    console.log("Sending cart to server:", cart);
        
    fetch(checkoutSessionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      // Send the cart data to the server
      body: JSON.stringify(cart),
    })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => {
            try {
              // Try to parse as JSON
              const data = JSON.parse(text);
              throw new Error(data.error || `HTTP error! Status: ${response.status}`);
            } catch (e) {
              // If not JSON, just throw the status
              throw new Error(`HTTP error! Status: ${response.status}. Server response was not valid JSON.`);
            }
          });
        }
        return response.json();
      })
      .then(data => {
        if (data.sessionUrl) {
          // Redirect the user to Stripe's hosted checkout page.
          window.location.href = data.sessionUrl;
        } else {
          console.error("Error creating checkout session:", data.error);
          alert("Error creating checkout session: " + data.error);
        }
      })
      .catch(error => {
        console.error("Error:", error);
        alert("Error processing checkout: " + error.message);
      });
  }
  

  const checkoutButton = document.getElementById("checkoutButton");
  checkoutButton.addEventListener("click", returnCheckout);

  // Add event listener for the Clear Cart button
  const clearCartButton = document.getElementById("clearCartButton");
  if (clearCartButton) {
    clearCartButton.addEventListener("click", function() {
      clearCartAndCoupon();
      
      // Show a temporary message to the user
      const notificationArea = document.getElementById("notificationArea");
      if (notificationArea) {
        notificationArea.textContent = "Cart cleared successfully!";
        notificationArea.classList.remove("hidden");
        
        // Hide the message after 3 seconds
        setTimeout(function() {
          notificationArea.classList.add("hidden");
        }, 3000);
      }
    });
  }

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
    
    // Check if there's a coupon applied and recalculate the total
    if (cart.coupon_code && cart.discount_percentage) {
      // Apply the discount to the cart
      applyDiscountToCart(cart.discount_percentage);
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
    // Validate inputs
    const parsedTicketPrice = parseFloat(ticketPrice);
    const parsedCrewSize = parseInt(crewSize, 10);
    
    if (isNaN(parsedTicketPrice) || parsedTicketPrice <= 0) {
      console.error("Invalid ticket price:", ticketPrice);
      return;
    }
    
    if (isNaN(parsedCrewSize) || parsedCrewSize <= 0) {
      console.error("Invalid crew size:", crewSize);
      return;
    }
    
    if (!ticketId || !ticketName || !crewId || !crewName || !eventId) {
      console.error("Missing required crew ticket information");
      return;
    }
    
    // Generate a unique cart key (e.g., "TICKETID_crew_CREWID")
    const cartKey = `${ticketId}_crew_${crewId}`;

    // Check if this crew ticket already exists in the cart
    if (!cart[cartKey]) {
      cart[cartKey] = {
        name: `${String(ticketName)} (${String(crewName)})`,
        price: parsedTicketPrice,
        quantity: parsedCrewSize,
        ticketId: String(ticketId),
        crewId: String(crewId),
        eventId: String(eventId),
      };
    } else {
      // If the user picks the same crew ticket again,
      // just add more quantity. Usually you'd add `crewSize`,
      // but you can decide whether to let them add it multiple times.
      cart[cartKey].quantity += parsedCrewSize;
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

  // Coupon related functions
  function setupCouponElements() {
    // Create the couponMessage element if it doesn't exist
    if (!couponMessage) {
      couponMessage = document.createElement("div");
      couponMessage.id = "couponMessage";
      couponMessage.className = "mt-2 text-sm hidden";
      
      // Insert it after the coupon input
      if (couponCodeInput && couponCodeInput.parentNode) {
        couponCodeInput.parentNode.insertBefore(couponMessage, couponCodeInput.nextSibling);
      }
    }
    
    // Create the couponCodeError element if it doesn't exist
    if (!couponCodeError) {
      couponCodeError = document.createElement("div");
      couponCodeError.id = "couponCodeError";
      couponCodeError.className = "text-red-500 text-sm mt-1 hidden";
      couponCodeError.textContent = "Please enter a coupon code";
      
      // Insert it after the coupon input
      if (couponCodeInput && couponCodeInput.parentNode) {
        couponCodeInput.parentNode.insertBefore(couponCodeError, couponMessage);
      }
    }
    
    // Get the existing removeCouponButton from the HTML
    const removeCouponButton = document.getElementById("removeCouponButton");
    
    // No need to create or insert the button as it's already in the HTML
    return removeCouponButton;
  }

  function setupCouponHandlers() {
    const removeCouponButton = document.getElementById("removeCouponButton");
    
    // Check if a coupon is already in the cart when the page loads
    const cart = JSON.parse(localStorage.getItem('cart') || '{}');
    if (cart.coupon_code) {
      // Set the input value to the coupon code
      couponCodeInput.value = cart.coupon_code;
      
      // Disable the input field
      couponCodeInput.disabled = true;
      couponCodeInput.classList.add("bg-gray-100");
      
      // Hide the Apply button container and show the Remove button container
      document.getElementById("applyButtonContainer").classList.add("hidden");
      document.getElementById("removeCouponButtonContainer").classList.remove("hidden");
      
      // Disable the Apply button
      couponCodeButton.disabled = true;
      
      // Show a message that the coupon is applied
      couponMessage.textContent = "Coupon applied";
      couponMessage.classList.remove("hidden", "text-red-500", "text-gray-500");
      couponMessage.classList.add("text-green-500");
      
      // Verify the coupon is still valid by making a server request
      const eventId = eventIdElement.value;
      if (eventId) {
          fetch('/ticketing/coupon/apply/', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
              },
              body: JSON.stringify({
                  'coupon_code': cart.coupon_code,
                  'event_id': eventId
              })
          })
          .then(response => response.json())
          .then(data => {
              if (data.success && data.discount_percentage) {
                  // Store the discount percentage in the cart
                  cart.discount_percentage = parseFloat(data.discount_percentage);
                  
                  // Apply the discount to all items in the cart
                  applyDiscountToCart(data.discount_percentage);
              }
          })
          .catch(error => {
              console.error('Error verifying coupon:', error);
              // If there's an error, we'll leave the UI as is but won't apply the discount
          });
      }
    }
    
    // Add event listener for the remove coupon button
    removeCouponButton.addEventListener("click", function() {
      const couponCodeInput = document.getElementById("couponCodeInput");
      const couponMessage = document.getElementById("couponMessage");
      
      // Remove coupon from cart
      let cart = JSON.parse(localStorage.getItem('cart') || '{}');
      delete cart.coupon_code;
      delete cart.discount_percentage;
      
      // Reset prices to original values before updating localStorage
      resetPrices();
      
      // Update localStorage with the updated cart
      localStorage.setItem('cart', JSON.stringify(cart));
      
      // Update server-side cart
      fetch('/ticketing/cart/update/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
          },
          body: JSON.stringify(cart)
      })
      .then(response => response.json())
      .then(data => {
          console.log('Cart updated on server:', data);
          
          // Reset the UI
          couponCodeInput.disabled = false;
          couponCodeInput.classList.remove("bg-gray-100");
          couponCodeInput.value = "";
          
          // Show the Apply button container and hide the Remove button container
          document.getElementById("applyButtonContainer").classList.remove("hidden");
          document.getElementById("removeCouponButtonContainer").classList.add("hidden");
          
          // Reset the Apply button
          couponCodeButton.textContent = "Apply";
          couponCodeButton.disabled = false;
          couponCodeButton.style.opacity = 1;
          
          // Hide the remove coupon button
          removeCouponButton.classList.add("hidden");
          
          couponMessage.textContent = "Coupon removed";
          couponMessage.classList.remove("text-green-500", "text-red-500", "hidden");
          couponMessage.classList.add("text-gray-500");
      })
      .catch(error => {
          console.error('Error updating cart on server:', error);
          couponMessage.textContent = "Error removing coupon";
          couponMessage.classList.remove("text-green-500", "text-gray-500", "hidden");
          couponMessage.classList.add("text-red-500");
      });
    });
    
    couponCodeButton.addEventListener("click", function () {
      const couponCodeValue = couponCodeInput.value;
      const eventId = eventIdElement.value;
      
      if (!couponCodeValue) {
          couponCodeError.style.display = "flex";
          return;
      } else {
          couponCodeError.style.display = "none";
      }
      
      // Disable button during request
      couponCodeButton.disabled = true;
      couponCodeButton.style.opacity = 0.5;
      couponMessage.textContent = "Processing...";
      couponMessage.classList.remove("hidden");
      couponMessage.classList.remove("text-red-500", "text-green-500");
      couponMessage.classList.add("text-gray-500");

      // Get the CSRF token from the page
      const csrfTokenElement = document.querySelector('input[name="csrfmiddlewaretoken"]');
      if (!csrfTokenElement) {
          console.error('CSRF token not found');
          couponMessage.textContent = "Error: CSRF token not found";
          couponMessage.classList.remove("text-gray-500", "text-green-500");
          couponMessage.classList.add("text-red-500");
          couponCodeButton.disabled = false;
          couponCodeButton.style.opacity = 1;
          return;
      }
      
      const csrfToken = csrfTokenElement.value;
      
      // Use fetch API to send the coupon code to our new endpoint
      fetch('/ticketing/coupon/apply/', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
              'coupon_code': couponCodeValue,
              'event_id': eventId
          })
      })
      .then(response => {
          // First check if the response is ok
          if (!response.ok) {
              // Try to parse as JSON first
              return response.text().then(text => {
                  try {
                      // Try to parse as JSON
                      const data = JSON.parse(text);
                      throw new Error(data.message || `HTTP error! Status: ${response.status}`);
                  } catch (e) {
                      // If not JSON, just throw the status
                      throw new Error(`HTTP error! Status: ${response.status}. Server response was not valid JSON.`);
                  }
              });
          }
          
          // If response is ok, try to parse as JSON
          return response.text().then(text => {
              try {
                  return JSON.parse(text);
              } catch (e) {
                  throw new Error('Response was not valid JSON');
              }
          });
      })
      .then(data => {
        console.log("Success response:", data);
        couponMessage.textContent = "Coupon applied successfully! (" + data.discount_percentage + "% off)";
        couponMessage.classList.remove("hidden", "text-red-500", "text-gray-500");
        couponMessage.classList.add("text-green-500");
        
        // Disable the input field when a valid coupon is applied
        couponCodeInput.disabled = true;
        couponCodeInput.classList.add("bg-gray-100");
        
        // Hide the Apply button container and show the Remove button container
        document.getElementById("applyButtonContainer").classList.add("hidden");
        document.getElementById("removeCouponButtonContainer").classList.remove("hidden");
        
        // Reset the Apply button
        couponCodeButton.textContent = "Apply";
        couponCodeButton.disabled = false;
        couponCodeButton.style.opacity = 1;
        
        // Update cart with the coupon code
        updateCartWithCoupon(couponCodeValue, data.discount_percentage);
      })
      .catch(error => {
          console.error("Error:", error);
          couponMessage.textContent = "Failed to process coupon code. (codes are case sensitive)";
          couponMessage.classList.remove("hidden", "text-green-500", "text-gray-500");
          couponMessage.classList.add("text-red-500");
          
          // Re-enable button on error
          couponCodeButton.disabled = false;
          couponCodeButton.style.opacity = 1;
      });
    });
  }

  function updateCartWithCoupon(couponCode, discountPercentage) {
    // Validate inputs
    if (!couponCode) {
      console.error("Invalid coupon code");
      return;
    }
    
    const validDiscount = parseFloat(discountPercentage);
    if (isNaN(validDiscount) || validDiscount < 0 || validDiscount > 100) {
      console.error("Invalid discount percentage:", discountPercentage);
      return;
    }
    
    // Add the coupon code and discount percentage to the cart
    cart.coupon_code = couponCode;
    cart.discount_percentage = validDiscount;
    
    // Save the updated cart back to localStorage
    localStorage.setItem('cart', JSON.stringify(cart));
    
    // Update the server-side cart
    fetch('/ticketing/cart/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
        },
        body: JSON.stringify(cart)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.text().then(text => {
            try {
                return JSON.parse(text);
            } catch (e) {
                throw new Error('Response was not valid JSON');
            }
        });
    })
    .then(data => {
        console.log('Cart updated on server:', data);
        
        // Apply the discount to all items in the cart
        if (validDiscount > 0) {
            applyDiscountToCart(validDiscount);
        }
    })
    .catch(error => {
        console.error('Error updating cart on server:', error);
    });
  }
  
  // Function to reset prices to their original values
  function resetPrices() {
    // Reset prices in the cart
    for (let ticketId in cart) {
      // Skip non-ticket properties
      if (ticketId === 'coupon_code' || ticketId === 'discount_percentage') {
        continue;
      }
      
      // Ensure we have a valid ticket object
      if (!cart[ticketId] || typeof cart[ticketId] !== 'object') {
        continue;
      }
      
      // Reset to original price if available
      if (cart[ticketId].original_price) {
        const originalPrice = parseFloat(cart[ticketId].original_price);
        if (!isNaN(originalPrice)) {
          cart[ticketId].price = originalPrice;
        }
        delete cart[ticketId].original_price;
      }
    }
    
    // Remove discount information from cart
    delete cart.discount_percentage;
    
    // Find all price elements
    const priceElements = document.querySelectorAll('.ticket-price');
    const totalElement = document.getElementById('checkoutTotal');
    
    // Reset each price element to its original value
    priceElements.forEach(element => {
        const originalPrice = element.getAttribute('data-original-price');
        if (originalPrice) {
            element.textContent = '$' + parseFloat(originalPrice).toFixed(2);
            // Remove the data attribute to ensure clean state
            element.removeAttribute('data-original-price');
        }
    });
    
    // Update the cart display with the reset prices
    updateCartDisplay();
    
    // Save the updated cart to localStorage and server
    saveCartToServer();
  }
  
  // Function to update the displayed prices with the discount
  function updateDisplayedPrices(discountPercentage) {
    // Validate discount percentage
    const validDiscount = parseFloat(discountPercentage);
    if (isNaN(validDiscount) || validDiscount < 0 || validDiscount > 100) {
      console.error("Invalid discount percentage:", discountPercentage);
      return;
    }
    
    // Find all price elements
    const priceElements = document.querySelectorAll('.ticket-price');
    const totalElement = document.getElementById('checkoutTotal');
    
    // Calculate the discount multiplier (e.g., 10% discount = 0.9 multiplier)
    const discountMultiplier = 1 - (validDiscount / 100);
    
    // Update each price element
    priceElements.forEach(element => {
        // Get the original price, either from the data attribute or from the current text
        let originalPrice;
        if (element.hasAttribute('data-original-price')) {
            originalPrice = parseFloat(element.getAttribute('data-original-price'));
        } else {
            const priceText = element.textContent.replace('$', '').trim();
            originalPrice = parseFloat(priceText);
            // Store the original price for future reference
            element.setAttribute('data-original-price', originalPrice);
        }
        
        // Skip if the original price is not a valid number
        if (isNaN(originalPrice)) {
            console.error("Invalid original price:", element.textContent);
            return;
        }
        
        // Calculate the discounted price
        const discountedPrice = (originalPrice * discountMultiplier).toFixed(2);
        
        // Update the displayed price
        element.textContent = '$' + discountedPrice;
    });
    
    // The checkout total is already updated by updateCartDisplay which uses the cart prices
    // We don't need to manually update it here, as that could lead to double-discounting
  }

  // Function to apply discount to all items in the cart
  function applyDiscountToCart(discountPercentage) {
    // Validate discount percentage
    const validDiscount = parseFloat(discountPercentage);
    if (isNaN(validDiscount) || validDiscount < 0 || validDiscount > 100) {
      console.error("Invalid discount percentage:", discountPercentage);
      return;
    }
    
    // Store the discount percentage in the cart for future reference
    cart.discount_percentage = validDiscount;
    
    // Calculate the discount multiplier (e.g., 10% discount = 0.9 multiplier)
    const discountMultiplier = 1 - (validDiscount / 100);
    
    // Apply the discount to each item in the cart
    for (let ticketId in cart) {
      // Skip non-ticket properties like coupon_code and discount_percentage
      if (ticketId === 'coupon_code' || ticketId === 'discount_percentage') {
        continue;
      }
      
      // Ensure we have a valid ticket object
      if (!cart[ticketId] || typeof cart[ticketId] !== 'object') {
        continue;
      }
      
      // Store the original price if not already stored
      if (!cart[ticketId].original_price) {
        // Make sure price is a valid number
        const originalPrice = parseFloat(cart[ticketId].price);
        if (isNaN(originalPrice)) {
          console.error("Invalid price for ticket:", ticketId, cart[ticketId]);
          continue;
        }
        cart[ticketId].original_price = originalPrice;
      }
      
      // Apply the discount to the price
      const originalPrice = parseFloat(cart[ticketId].original_price);
      cart[ticketId].price = parseFloat((originalPrice * discountMultiplier).toFixed(2));
    }
    
    // Update the cart display to reflect the new prices
    updateCartDisplay();
    
    // Update the displayed prices in the UI
    updateDisplayedPrices(validDiscount);
    
    // Save the updated cart to localStorage and server
    saveCartToServer();
  }
});