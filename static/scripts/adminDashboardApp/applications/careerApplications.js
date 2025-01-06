document.addEventListener('DOMContentLoaded', function () {
    // Get all applicant cards
    const applicantCards = document.querySelectorAll('.applicant-card');

    // Loop through each applicant card
    applicantCards.forEach(card => {
        // Add click event listener to each card
        card.addEventListener('click', function () {
            // Get the ID of the corresponding modal (it uses the same loop counter as the applicant)
            const modalId = `#viewHostApplicationModal-${card.getAttribute('data-counter')}`;
            const modal = document.querySelector(modalId);

            // Display the modal by removing the 'hidden' class
            if (modal) {
                modal.classList.remove('hidden');
            }
        });
    });

    // Close button functionality for modals
    const closeButtons = document.querySelectorAll('#hideModalButton');
    closeButtons.forEach(button => {
        button.addEventListener('click', function () {
            // Get the closest modal (parent element) to the close button and hide it
            const modal = button.closest('.hidden') || button.closest('.modalContentCard').parentElement.parentElement;
            if (modal) {
                modal.classList.add('hidden');
            }
        });
    });
});
