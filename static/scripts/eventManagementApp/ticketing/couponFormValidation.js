/**
 * Coupon Form Validation
 * Provides real-time validation for coupon creation form
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get form and form elements
    const couponForm = document.getElementById('couponCreateForm');
    const couponCodeInput = document.getElementById('id_code');
    const discountPercentageInput = document.getElementById('id_discount_percentage');
    const submitButton = document.querySelector('.createCouponButton');
    
    // Error display elements
    const codeError = document.getElementById('coupon_code_error');
    const discountError = document.getElementById('coupon_discount_percentage_error');
    
    // Disable button initially
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.classList.add('opacity-50', 'cursor-not-allowed');
    }
    
    // Validation rules
    function validateCouponCode() {
        const value = couponCodeInput.value.trim();
        if (!value) {
            codeError.textContent = 'Coupon code is required';
            codeError.classList.remove('hidden');
            couponCodeInput.classList.add('border-red-500');
            return false;
        } else if (value.length > 20) {
            codeError.textContent = 'Coupon code must be less than 20 characters';
            codeError.classList.remove('hidden');
            couponCodeInput.classList.add('border-red-500');
            return false;
        } else if (!/^[A-Za-z0-9_-]+$/.test(value)) {
            codeError.textContent = 'Only letters, numbers, underscores and hyphens are allowed';
            codeError.classList.remove('hidden');
            couponCodeInput.classList.add('border-red-500');
            return false;
        } else {
            codeError.classList.add('hidden');
            couponCodeInput.classList.remove('border-red-500');
            couponCodeInput.classList.add('border-green-500');
            return true;
        }
    }
    
    function validateDiscountPercentage() {
        const value = discountPercentageInput.value.trim();
        const percentageRegex = /^[0-9]+$/;
        
        if (!value) {
            discountError.textContent = 'Discount percentage is required';
            discountError.classList.remove('hidden');
            discountPercentageInput.classList.add('border-red-500');
            return false;
        } else if (!percentageRegex.test(value)) {
            discountError.textContent = 'Please enter a valid number';
            discountError.classList.remove('hidden');
            discountPercentageInput.classList.add('border-red-500');
            return false;
        } else if (parseInt(value) < 1 || parseInt(value) > 100) {
            discountError.textContent = 'Percentage must be between 1 and 100';
            discountError.classList.remove('hidden');
            discountPercentageInput.classList.add('border-red-500');
            return false;
        } else {
            discountError.classList.add('hidden');
            discountPercentageInput.classList.remove('border-red-500');
            discountPercentageInput.classList.add('border-green-500');
            return true;
        }
    }
    
    function validateForm() {
        const isCodeValid = validateCouponCode();
        const isDiscountValid = validateDiscountPercentage();
        
        // Enable or disable submit button based on validation results
        if (submitButton) {
            if (isCodeValid && isDiscountValid) {
                submitButton.disabled = false;
                submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                submitButton.disabled = true;
                submitButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }
        
        return isCodeValid && isDiscountValid;
    }
    
    // Add event listeners for real-time validation
    if (couponCodeInput) {
        couponCodeInput.addEventListener('input', function() {
            this.value = this.value.toUpperCase();
            validateForm();
        });
        couponCodeInput.addEventListener('blur', validateForm);
    }
    
    if (discountPercentageInput) {
        discountPercentageInput.addEventListener('input', validateForm);
        discountPercentageInput.addEventListener('blur', validateForm);
    }
    
    // Form submission handler
    if (couponForm) {
        couponForm.addEventListener('submit', function(event) {
            if (!validateForm()) {
                event.preventDefault();
            } else {
                // Show loading state
                const submitBtn = this.querySelector('button[type="submit"]');
                const loadingSpinner = submitBtn.querySelector('.animate-spin');
                const btnText = submitBtn.querySelector('span.relative.z-10');
                
                loadingSpinner.classList.remove('hidden');
                btnText.textContent = 'Creating...';
                submitBtn.disabled = true;
                submitBtn.classList.add('opacity-90');
            }
        });
    }
    
    // Run validation once on page load to ensure button state is correct
    validateForm();
});
