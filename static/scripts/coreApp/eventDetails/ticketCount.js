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
  
  // Early return if coupon elements don't exist
  if (couponCodeButton && eventIdElement) {
    setupCouponElements();
    setupCouponHandlers();
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
    updateCartWithCoupon()
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
    
    // Copy only valid ticket items to the cart
    for (const [key, value] of Object.entries(cartFromStorage)) {
      if (key === 'coupon_code') {
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
        
        // Only add items with valid values
        if (!isNaN(ticketItem.price) && !isNaN(ticketItem.quantity) && 
            ticketItem.quantity > 0 && ticketItem.price > 0) {
          cart[key] = ticketItem;
        }
      }
    }
    
    // Check if we have any valid tickets after filtering
    if (Object.keys(cart).length === 0 || 
        (Object.keys(cart).length === 1 && 'coupon_code' in cart)) {
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
    
    // Create a remove coupon button element but don't add it to the DOM yet
    const removeCouponButton = document.createElement("button");
    removeCouponButton.id = "removeCouponButton";
    removeCouponButton.textContent = "Remove Coupon";
    removeCouponButton.className = "ml-2 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 rounded-2xl";
    removeCouponButton.style.display = "none"; // Hide it initially
    
    // Insert the remove button after the apply button
    if (couponCodeButton.parentNode) {
      couponCodeButton.parentNode.insertBefore(removeCouponButton, couponCodeButton.nextSibling);
    }

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
      
      // Change the button text to indicate the coupon is applied
      couponCodeButton.textContent = "Applied";
      couponCodeButton.classList.add("bg-green-500");
      couponCodeButton.disabled = true;
      
      // Show the remove coupon button
      removeCouponButton.style.display = "inline-block";
      
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
                  // Update prices with the discount
                  updateDisplayedPrices(data.discount_percentage);
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
          
          couponCodeButton.textContent = "Apply";
          couponCodeButton.classList.remove("bg-green-500");
          couponCodeButton.disabled = false;
          couponCodeButton.style.opacity = 1;
          
          removeCouponButton.style.display = "none";
          
          couponMessage.textContent = "Coupon removed";
          couponMessage.classList.remove("text-green-500", "text-red-500", "hidden");
          couponMessage.classList.add("text-gray-500");
          
          // Reset prices to original values
          resetPrices();
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
          couponMessage.textContent = data.message || "Coupon applied successfully!";
          couponMessage.classList.remove("hidden", "text-red-500", "text-gray-500");
          couponMessage.classList.add("text-green-500");
          
          // Disable the input field when a valid coupon is applied
          couponCodeInput.disabled = true;
          couponCodeInput.classList.add("bg-gray-100");
          
          // Change the button text to indicate the coupon is applied
          couponCodeButton.textContent = "Applied";
          couponCodeButton.classList.add("bg-green-500");
          couponCodeButton.disabled = true;
          
          // Show the remove coupon button
          removeCouponButton.style.display = "inline-block";
          
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
    // Get the current cart from localStorage or initialize an empty one
    let cart = JSON.parse(localStorage.getItem('cart') || '{}');
    
    // Add the coupon code to the cart
    cart.coupon_code = couponCode;
    
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
        
        // Update the displayed prices if discount was applied
        if (discountPercentage > 0) {
            updateDisplayedPrices(discountPercentage);
        }
    })
    .catch(error => {
        console.error('Error updating cart on server:', error);
    });
  }
  
  // Function to reset prices to their original values
  function resetPrices() {
    // Find all price elements
    const priceElements = document.querySelectorAll('.ticket-price');
    const totalElement = document.getElementById('checkoutTotal');
    
    // Reset each price element to its original value
    priceElements.forEach(element => {
        const originalPrice = element.getAttribute('data-original-price');
        if (originalPrice) {
            element.textContent = '$' + parseFloat(originalPrice).toFixed(2);
        }
    });
    
    // Reset the total if it exists
    if (totalElement) {
        const originalTotal = totalElement.getAttribute('data-original-total');
        if (originalTotal) {
            totalElement.textContent = '$' + parseFloat(originalTotal).toFixed(2);
        }
    }
  }
  
  // Function to update the displayed prices with the discount
  function updateDisplayedPrices(discountPercentage) {
    // Find all price elements
    const priceElements = document.querySelectorAll('.ticket-price');
    const totalElement = document.getElementById('checkoutTotal');
    
    // Calculate the discount multiplier (e.g., 10% discount = 0.9 multiplier)
    const discountMultiplier = 1 - (discountPercentage / 100);
    
    // Update each price element
    priceElements.forEach(element => {
        const originalPrice = parseFloat(element.getAttribute('data-original-price') || element.textContent.replace('$', ''));
        const discountedPrice = (originalPrice * discountMultiplier).toFixed(2);
        
        // Store the original price if not already stored
        if (!element.hasAttribute('data-original-price')) {
            element.setAttribute('data-original-price', originalPrice);
        }
        
        // Update the displayed price
        element.textContent = '$' + discountedPrice;
    });
    
    // Update the total if it exists
    if (totalElement) {
        const originalTotal = parseFloat(totalElement.getAttribute('data-original-total') || totalElement.textContent.replace('$', ''));
        const discountedTotal = (originalTotal * discountMultiplier).toFixed(2);
        
        // Store the original total if not already stored
        if (!totalElement.hasAttribute('data-original-total')) {
            totalElement.setAttribute('data-original-total', originalTotal);
        }
        
        // Update the displayed total
        totalElement.textContent = '$' + discountedTotal;
    }
  }
});