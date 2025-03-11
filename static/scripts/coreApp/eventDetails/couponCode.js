document.addEventListener("DOMContentLoaded", function () {
    const couponCodeButton = document.getElementById("couponCodeButton");
    if (!couponCodeButton) return; // Exit if button doesn't exist
    
    couponCodeButton.addEventListener("click", function () {
        const couponCodeInput = document.getElementById("couponCodeInput");
        const couponCodeValue = couponCodeInput.value; // Fixed: removed parentheses
        const couponCodeError = document.getElementById("couponCodeError");
        const couponMessage = document.getElementById("couponMessage");
        const url = document.getElementById("coupon-url").value; // Fixed: removed parentheses
        
        if (!couponCodeValue) {
            couponCodeError.style.display = "flex"; // Fixed: setting display property correctly
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
        
        console.log("Sending request to:", url);
        console.log("With coupon code:", couponCodeValue);
        
        // Use fetch API instead of jQuery for better error handling
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: new URLSearchParams({
                'eventAction': 'applyCouponCode',
                'couponCode': couponCodeValue
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.message || `HTTP error! Status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log("Success response:", data);
            couponMessage.textContent = data.message || "Coupon applied successfully!";
            couponMessage.classList.remove("hidden", "text-red-500", "text-gray-500");
            couponMessage.classList.add("text-green-500");
            
            // Update cart total if provided in response
            if (data.new_total) {
                const checkoutTotal = document.getElementById("checkoutTotal");
                if (checkoutTotal) {
                    checkoutTotal.textContent = "$" + parseFloat(data.new_total).toFixed(2);
                }
            }
        })
        .catch(error => {
            console.error("Error:", error);
            couponMessage.textContent = error.message || "Failed to process coupon code.";
            couponMessage.classList.remove("hidden", "text-green-500", "text-gray-500");
            couponMessage.classList.add("text-red-500");
        })
        .finally(() => {
            // Re-enable button regardless of outcome
            couponCodeButton.disabled = false;
            couponCodeButton.style.opacity = 1;
        });
    });
});