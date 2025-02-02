document.addEventListener('DOMContentLoaded', function () {
    const createTicketButtonFirst = document.getElementById('createTicketButtonFirst');
    const closeTicketModal = document.getElementById('closeCreateTicketModalButton');
    const createTicketModal = document.getElementById("ticketCreationModal")

    if (createTicketButtonFirst) {
        createTicketButtonFirst.addEventListener('click', function () {
            createTicketModal.classList.remove('hidden');
        });
    }

    if (closeTicketModal) {
        closeTicketModal.addEventListener('click', function () {
            createTicketModal.classList.add('hidden');
        });
    }

    const editButtons = document.querySelectorAll('[id^="editTicketButton-"]');
    editButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const ticketId = btn.getAttribute('data-ticketid');
            const modal = document.getElementById(`ticketEditModal-${ticketId}`);
            if (modal) {
                modal.classList.remove('hidden');
            }
        });
    });

    const closeButtons = document.querySelectorAll('[id^="closeEditTicketModalButton-"]');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const ticketId = btn.getAttribute('data-ticketid');
            const modal = document.getElementById(`ticketEditModal-${ticketId}`);
            if (modal) {
                modal.classList.add('hidden');
            }
        });
    });
});