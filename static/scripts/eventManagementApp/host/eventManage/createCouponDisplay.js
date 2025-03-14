document.addEventListener('DOMContentLoaded', function() {
    // Get the coupon modal element
    const couponModal = document.getElementById('couponCreationModal');
    
    // Get the button that opens the coupon modal
    const createCouponButtons = document.querySelectorAll('#createCouponButton');
    
    // Get the button that closes the coupon modal
    const closeCouponModalButton = document.getElementById('closeCreateCouponModalButton');
    
    // Function to open the coupon modal
    function openCouponModal() {
        if (couponModal) {
            couponModal.classList.remove('hidden');
        }
    }
    
    // Function to close the coupon modal
    function closeCouponModal() {
        if (couponModal) {
            couponModal.classList.add('hidden');
        }
    }
    
    // Add click event listeners to all create coupon buttons
    createCouponButtons.forEach(button => {
        button.addEventListener('click', openCouponModal);
    });
    
    // Add click event listener to close button
    if (closeCouponModalButton) {
        closeCouponModalButton.addEventListener('click', closeCouponModal);
    }
    
    // Close the modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === couponModal) {
            closeCouponModal();
        }
    });
}); 