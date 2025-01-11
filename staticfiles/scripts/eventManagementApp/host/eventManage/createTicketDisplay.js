document.addEventListener('DOMContentLoaded', function () {
    const createTicketButtonFirst = document.getElementById('createTicketButtonFirst');
    const createTicketButtonSecond = document.getElementById('createTicketButtonSecond');
    const closeTicketModal = document.getElementById('closeCreateTicketModalButton');
    const createTicketModal = document.getElementById("ticketCreationModal")

    createTicketButtonFirst.addEventListener('click', function () {
        createTicketModal.classList.remove('hidden');
    });

    createTicketButtonSecond.addEventListener('click', function () {
        createTicketModal.classList.remove('hidden');
    });

    closeTicketModal.addEventListener('click', function () {
        createTicketModal.classList.add('hidden');
    });
});