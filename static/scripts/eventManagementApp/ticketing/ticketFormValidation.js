document.addEventListener('DOMContentLoaded', function() {
    // Get form and form elements
    const ticketForm = document.getElementById('ticketCreateForm');
    const ticketNameInput = document.getElementById('id_ticket_name');
    const ticketPriceInput = document.getElementById('id_ticket_price');
    const ticketQuantityInput = document.getElementById('id_ticket_quantity');
    const ticketDescriptionInput = document.getElementById('id_ticket_description');
    const submitButton = document.querySelector('.createPaidTicketButton');

    // Disable button initially
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.classList.add('opacity-50', 'cursor-not-allowed');
    }

    // Error display elements
    const nameError = document.getElementById('ticket_name_error');
    const priceError = document.getElementById('ticket_price_error');
    const quantityError = document.getElementById('ticket_quantity_error');
    const descriptionError = document.getElementById('ticket_description_error');

    // Validation rules
    function validateTicketName() {
        const value = ticketNameInput.value.trim();
        if (!value) {
            nameError.textContent = 'Ticket name is required';
            nameError.classList.remove('hidden');
            ticketNameInput.classList.add('border-red-500');
            return false;
        } else if (value.length > 100) {
            nameError.textContent = 'Ticket name must be less than 100 characters';
            nameError.classList.remove('hidden');
            ticketNameInput.classList.add('border-red-500');
            return false;
        } else {
            nameError.classList.add('hidden');
            ticketNameInput.classList.remove('border-red-500');
            return true;
        }
    }

    function validateTicketPrice() {
        const value = ticketPriceInput.value.trim();
        const priceRegex = /^\d+(\.\d{1,2})?$/;
        
        if (!value) {
            priceError.textContent = 'Ticket price is required';
            priceError.classList.remove('hidden');
            ticketPriceInput.classList.add('border-red-500');
            return false;
        } else if (!priceRegex.test(value)) {
            priceError.textContent = 'Please enter a valid price (digits only)';
            priceError.classList.remove('hidden');
            ticketPriceInput.classList.add('border-red-500');
            return false;
        } else if (parseFloat(value) < 1) {
            priceError.textContent = 'Price must be at least $1';
            priceError.classList.remove('hidden');
            ticketPriceInput.classList.add('border-red-500');
            return false;
        } else {
            priceError.classList.add('hidden');
            ticketPriceInput.classList.remove('border-red-500');
            return true;
        }
    }

    function validateTicketQuantity() {
        const value = ticketQuantityInput.value.trim();
        const quantityRegex = /^\d+$/;
        
        if (!value) {
            quantityError.textContent = 'Ticket quantity is required';
            quantityError.classList.remove('hidden');
            ticketQuantityInput.classList.add('border-red-500');
            return false;
        } else if (!quantityRegex.test(value)) {
            quantityError.textContent = 'Please enter a valid number';
            quantityError.classList.remove('hidden');
            ticketQuantityInput.classList.add('border-red-500');
            return false;
        } else if (parseInt(value) <= 0) {
            quantityError.textContent = 'Quantity must be greater than 0';
            quantityError.classList.remove('hidden');
            ticketQuantityInput.classList.add('border-red-500');
            return false;
        } else {
            quantityError.classList.add('hidden');
            ticketQuantityInput.classList.remove('border-red-500');
            return true;
        }
    }

    function validateTicketDescription() {
        const value = ticketDescriptionInput.value.trim();
        if (!value) {
            descriptionError.textContent = 'Ticket description is required';
            descriptionError.classList.remove('hidden');
            ticketDescriptionInput.classList.add('border-red-500');
            return false;
        } else if (value.length > 1000) {
            descriptionError.textContent = 'Description must be less than 1000 characters';
            descriptionError.classList.remove('hidden');
            ticketDescriptionInput.classList.add('border-red-500');
            return false;
        } else {
            descriptionError.classList.add('hidden');
            ticketDescriptionInput.classList.remove('border-red-500');
            return true;
        }
    }

    function validateForm() {
        const isNameValid = validateTicketName();
        const isPriceValid = validateTicketPrice();
        const isQuantityValid = validateTicketQuantity();
        const isDescriptionValid = validateTicketDescription();

        // Enable or disable submit button based on validation results
        if (submitButton) {
            if (isNameValid && isPriceValid && isQuantityValid && isDescriptionValid) {
                submitButton.disabled = false;
                submitButton.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                submitButton.disabled = true;
                submitButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }

        return isNameValid && isPriceValid && isQuantityValid && isDescriptionValid;
    }

    // Add event listeners for real-time validation
    if (ticketNameInput) {
        ticketNameInput.addEventListener('input', validateForm);
        ticketNameInput.addEventListener('blur', validateForm);
    }
    
    if (ticketPriceInput) {
        ticketPriceInput.addEventListener('input', validateForm);
        ticketPriceInput.addEventListener('blur', validateForm);
    }
    
    if (ticketQuantityInput) {
        ticketQuantityInput.addEventListener('input', validateForm);
        ticketQuantityInput.addEventListener('blur', validateForm);
    }
    
    if (ticketDescriptionInput) {
        ticketDescriptionInput.addEventListener('input', validateForm);
        ticketDescriptionInput.addEventListener('blur', validateForm);
    }

    // Form submission handler
    if (ticketForm) {
        ticketForm.addEventListener('submit', function(event) {
            if (!validateForm()) {
                event.preventDefault();
            }
        });
    }

    // Run validation once on page load to ensure button state is correct
    validateForm();
});
