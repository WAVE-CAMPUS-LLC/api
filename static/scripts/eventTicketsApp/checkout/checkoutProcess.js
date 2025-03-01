document.addEventListener("DOMContentLoaded", async function () {
  const stripeKey = document.getElementById("stripeKey").value;
  const stripe = Stripe(stripeKey);
  const processPaymentURL = document.getElementById("processPaymentUrl").value;
  const successPaymentURL = document.getElementById("successPaymentUrl").value;
  const failedPaymentURL = document.getElementById("failedPaymentURL").value;
  const paymentRedirectUrl =
    document.getElementById("paymentRedirectUrl").value;

  let elements;
  let paymentElement;

  // Get DOM elements with null checks
  const savedCardRadio = document.getElementById("saved-card");
  const newCardRadio = document.getElementById("new-card");
  const paymentElementDiv = document.getElementById("payment-element");
  const paymentError = document.getElementById("payment-error");

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrfToken = getCookie("csrftoken");

  // Function to get cart data with better error handling
  function getCartData() {
    try {
      // Try to get cart from hidden input first
      const cartInput = document.getElementById("cartData");
      if (cartInput && cartInput.value) {
        return JSON.parse(cartInput.value);
      }

      // Fallback to form data attribute
      const form = document.querySelector("form");
      if (form && form.dataset.cart) {
        return JSON.parse(form.dataset.cart);
      }

      // Final fallback to localStorage
      const localCart = localStorage.getItem("cart");
      if (localCart) {
        return JSON.parse(localCart);
      }

      throw new Error("No cart data found");
    } catch (error) {
      console.error("Error parsing cart data:", error);
      return null;
    }
  }

  async function initializeStripeElements() {
    try {
      const cart = getCartData();

      if (!cart || Object.keys(cart).length === 0) {
        throw new Error("Cart is empty");
      }

      // First, create a PaymentIntent on the server
      const response = await fetch(processPaymentURL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ cart }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();

      if (!data.clientSecret) {
        throw new Error("No client secret received from the server");
      }

      // Initialize Elements
      elements = stripe.elements({
        clientSecret: data.clientSecret,
        appearance: {
          theme: "stripe",
          variables: {
            colorPrimary: "#0570de",
            colorBackground: "#ffffff",
            colorText: "#30313d",
            colorDanger: "#df1b41",
            fontFamily: "Wanted-Variable, system-ui, sans-serif",
            borderRadius: "12px",
          },
        },
      });

      // Create and mount Payment Element
      const paymentElementDiv = document.getElementById("payment-element");
      if (paymentElementDiv) {
        paymentElement = elements.create("payment");
        paymentElement.mount("#payment-element");
        paymentElementDiv.classList.remove("hidden");
      }

      return data.clientSecret;
    } catch (error) {
      console.error("Error initializing Stripe:", error);
      const paymentError = document.getElementById("payment-error");
      if (paymentError) {
        paymentError.textContent =
          error.message ||
          "Failed to initialize payment form. Please try again.";
        paymentError.classList.remove("hidden");
      }
      throw error;
    }
  }

  // Initialize Stripe Elements based on the initial state
  if (!savedCardRadio || (newCardRadio && newCardRadio.checked)) {
    await initializeStripeElements();
  }

  // Only add event listeners if both radio buttons exist
  if (savedCardRadio && newCardRadio && paymentElementDiv) {
    savedCardRadio.addEventListener("change", function () {
      if (this.checked) {
        paymentElementDiv.classList.add("hidden");
        if (paymentElement) {
          paymentElement.destroy();
          elements = null;
          paymentElement = null;
        }
      }
    });

    newCardRadio.addEventListener("change", async function () {
      if (this.checked) {
        paymentElementDiv.classList.remove("hidden");
        await initializeStripeElements();
      }
    });
  }

  // Handle form submission
  const form = document.getElementById("checkoutForm");
  const payButton = document.getElementById("payButton");

  if (form && payButton) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      payButton.disabled = true;
      if (paymentError) paymentError.classList.add("hidden");

      try {
        if (savedCardRadio?.checked) {
          // Use saved payment method
          const response = await fetch(processPaymentURL, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({
              useStoredPaymentMethod: true,
              cart: getCartData(),
            }),
          });

          const result = await response.json();
          if (result.error) {
            throw new Error(result.error);
          } else {
            window.location.href = successPaymentURL;
          }
        } else {
          const name = `${document.getElementById("first_name")?.value || ""} ${
            document.getElementById("last_name")?.value || ""
          }`.trim();
          const email = document.getElementById("email")?.value;
          const result = await stripe.confirmPayment({
            elements,
            confirmParams: {
              return_url: paymentRedirectUrl,
              payment_method_data: {
                billing_details: {
                  name: name,
                  email: email,
                },
              },
            },
            redirect: "if_required",
          });

          const { error, paymentIntent } = result;

          if (error) {
            console.error("Payment failed:", error.message);
            window.location.href = failedPaymentURL;
          } else if (paymentIntent && paymentIntent.status === "succeeded") {
            window.location.href = successPaymentURL;
          } else {
            console.error("Unexpected payment status:", paymentIntent?.status);
            window.location.href = failedPaymentURL;
          }
        }
      } catch (error) {
        if (paymentError) {
          paymentError.textContent = error.message;
          paymentError.classList.remove("hidden");
        }
        payButton.disabled = false;
      }
    });
  }
});
