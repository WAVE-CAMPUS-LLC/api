/**
 * Enhanced Modal Interactions for Ticket and Coupon Creation
 * Provides smooth animations, improved accessibility, and better user experience
 */
document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements for better performance
    const createTicketButton = document.getElementById('createTicketButton');
    const createCouponButton = document.getElementById('createCouponButton');
    const ticketModal = document.getElementById('createTicketForm');
    const couponModal = document.getElementById('createCouponForm');
    const hideTicketModalButton = document.getElementById('hideTicketModalButton');
    const hideCouponModalButton = document.getElementById('hideCouponModalButton');
    const ticketForm = document.getElementById('ticketCreateForm');
    const couponForm = document.getElementById('couponCreateForm');
    const modalOverlays = document.querySelectorAll('.applicationPopupBg');
    
    // Modal animation classes
    const MODAL_ANIMATION_DURATION = 300; // ms
    
    // Helper function to add animation classes
    function animateModal(modal, isOpening) {
        const modalContent = modal.querySelector('.flex.flex-col.gap-5');
        
        if (isOpening) {
            // Show modal with fade-in and scale-up effect
            modal.classList.remove('hidden');
            modal.style.opacity = '0';
            if (modalContent) {
                modalContent.style.transform = 'scale(0.9)';
                modalContent.style.opacity = '0';
            }
            
            // Trigger reflow to ensure animation works
            void modal.offsetWidth;
            
            // Apply animations
            modal.style.transition = `opacity ${MODAL_ANIMATION_DURATION}ms ease-out`;
            modal.style.opacity = '1';
            
            if (modalContent) {
                modalContent.style.transition = `transform ${MODAL_ANIMATION_DURATION}ms ease-out, opacity ${MODAL_ANIMATION_DURATION}ms ease-out`;
                modalContent.style.transform = 'scale(1)';
                modalContent.style.opacity = '1';
            }
            
            // Focus the first form input for accessibility
            setTimeout(() => {
                const firstInput = modal.querySelector('input:not([type="hidden"])');
                if (firstInput) firstInput.focus();
            }, MODAL_ANIMATION_DURATION);
        } else {
            // Hide modal with fade-out and scale-down effect
            modal.style.transition = `opacity ${MODAL_ANIMATION_DURATION}ms ease-in`;
            modal.style.opacity = '0';
            
            if (modalContent) {
                modalContent.style.transition = `transform ${MODAL_ANIMATION_DURATION}ms ease-in, opacity ${MODAL_ANIMATION_DURATION}ms ease-in`;
                modalContent.style.transform = 'scale(0.9)';
                modalContent.style.opacity = '0';
            }
            
            // Actually hide the modal after animation completes
            setTimeout(() => {
                modal.classList.add('hidden');
                // Reset form if needed
                const form = modal.querySelector('form');
                if (form) form.reset();
                // Reset validation styles
                resetValidationStyles(modal);
            }, MODAL_ANIMATION_DURATION);
        }
    }
    
    // Reset validation styles when closing modal
    function resetValidationStyles(modal) {
        const inputs = modal.querySelectorAll('input, textarea');
        const errorMessages = modal.querySelectorAll('[id$="_error"]');
        
        inputs.forEach(input => {
            input.classList.remove('border-red-500');
            input.classList.remove('border-green-500');
        });
        
        errorMessages.forEach(error => {
            error.classList.add('hidden');
        });
    }
    
    // Close modal when clicking outside the content
    function setupOutsideClickHandler(modal) {
        modal.addEventListener('click', function(event) {
            // Only close if clicking directly on the backdrop (not on modal content)
            if (event.target === modal || event.target.classList.contains('applicationPopupBg')) {
                animateModal(modal, false);
            }
        });
    }
    
    // Setup keyboard accessibility (Escape key to close modals)
    function setupKeyboardAccessibility() {
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                if (!ticketModal.classList.contains('hidden')) {
                    animateModal(ticketModal, false);
                }
                if (!couponModal.classList.contains('hidden')) {
                    animateModal(couponModal, false);
                }
            }
        });
    }
    
    // Add visual feedback on form inputs
    function setupFormFeedback(form) {
        if (!form) return;
        
        const inputs = form.querySelectorAll('input:not([type="hidden"]), textarea');
        
        inputs.forEach(input => {
            // Add focus effects
            input.addEventListener('focus', function() {
                this.classList.add('ring-2', 'ring-gradient-start', 'ring-opacity-50');
            });
            
            input.addEventListener('blur', function() {
                this.classList.remove('ring-2', 'ring-gradient-start', 'ring-opacity-50');
            });
            
            // Add success indicator when valid
            input.addEventListener('input', function() {
                if (this.checkValidity() && this.value.trim() !== '') {
                    this.classList.add('border-green-500');
                    this.classList.remove('border-red-500');
                } else {
                    this.classList.remove('border-green-500');
                }
            });
        });
    }
    
    // Initialize event listeners
    function initializeEventListeners() {
        // Open modals with animation
        if (createTicketButton) {
            createTicketButton.addEventListener('click', function() {
                animateModal(ticketModal, true);
            });
        }
        
        if (createCouponButton) {
            createCouponButton.addEventListener('click', function() {
                animateModal(couponModal, true);
            });
        }
        
        // Close modals with animation
        if (hideTicketModalButton) {
            hideTicketModalButton.addEventListener('click', function() {
                animateModal(ticketModal, false);
            });
        }
        
        if (hideCouponModalButton) {
            hideCouponModalButton.addEventListener('click', function() {
                animateModal(couponModal, false);
            });
        }
        
        // Setup outside click handlers
        if (ticketModal) setupOutsideClickHandler(ticketModal);
        if (couponModal) setupOutsideClickHandler(couponModal);
        
        // Setup form feedback
        if (ticketForm) setupFormFeedback(ticketForm);
        if (couponForm) setupFormFeedback(couponForm);
    }
    
    // Initialize everything
    function initialize() {
        initializeEventListeners();
        setupKeyboardAccessibility();
        
        // Prevent the original simple show/hide from running
        // by removing the original event listeners
        if (createTicketButton) {
            const oldClickEvent = createTicketButton.onclick;
            createTicketButton.onclick = null;
        }
        
        if (createCouponButton) {
            const oldClickEvent = createCouponButton.onclick;
            createCouponButton.onclick = null;
        }
    }
    
    // Start the enhanced modal functionality
    initialize();
});
