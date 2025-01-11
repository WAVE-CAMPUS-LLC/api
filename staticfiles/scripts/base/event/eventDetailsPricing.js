document.addEventListener('DOMContentLoaded', function () {
    // Initialize cart count
    let cartCount = 0;

    // Function to update the cart display
    function updateCartDisplay() {
        const cartIcon = document.getElementById('shopping-cart-btn');
        const cartCountElem = document.getElementById('cart-count');
        if (cartCount > 0) {
            cartIcon.style.display = 'block';
            cartIcon.classList.add('shown');
            cartIcon.classList.add('bounce');
            cartCountElem.style.display = 'inline-block';
            setTimeout(() => {
                cartIcon.classList.remove('bounce');
            }, 500); // Remove bounce after animation completes
        } else {
            cartIcon.style.display = 'none';
            cartIcon.classList.remove('shown');
        }
    }

    // Initial call to check cart on page load
    updateCartDisplay();

    // Handle adding to the cart
    document.querySelectorAll('[id^="add-cart"]').forEach(button => {
        button.addEventListener('click', function () {
            const ticketId = this.getAttribute('data-ticket-id');
            const purchaseQuantityElem = document.getElementById('purchase-quantity-' + ticketId);
            const availableQuantityElem = document.getElementById('available-quantity-' + ticketId);

            if (purchaseQuantityElem && availableQuantityElem) {
                let purchaseQuantity = parseInt(purchaseQuantityElem.textContent);
                let availableQuantity = parseInt(availableQuantityElem.textContent.replace('Available: ', ''));

                if (availableQuantity > 0) {
                    purchaseQuantity += 1;
                    availableQuantity -= 1;
                    cartCount += 1;

                    purchaseQuantityElem.textContent = purchaseQuantity;
                    availableQuantityElem.textContent = 'Available: ' + availableQuantity;

                    updateCartDisplay();
                }
            }
        });
    });

    // Handle removing from the cart
    document.querySelectorAll('[id^="remove-cart"]').forEach(button => {
        button.addEventListener('click', function () {
            const ticketId = this.getAttribute('data-ticket-id');
            const purchaseQuantityElem = document.getElementById('purchase-quantity-' + ticketId);
            const availableQuantityElem = document.getElementById('available-quantity-' + ticketId);

            if (purchaseQuantityElem && availableQuantityElem) {
                let purchaseQuantity = parseInt(purchaseQuantityElem.textContent);
                let availableQuantity = parseInt(availableQuantityElem.textContent.replace('Available: ', ''));

                if (purchaseQuantity > 0) {
                    purchaseQuantity -= 1;
                    availableQuantity += 1;
                    cartCount -= 1;

                    purchaseQuantityElem.textContent = purchaseQuantity;
                    availableQuantityElem.textContent = 'Available: ' + availableQuantity;

                    updateCartDisplay();
                }
            }
        });
    });
});
