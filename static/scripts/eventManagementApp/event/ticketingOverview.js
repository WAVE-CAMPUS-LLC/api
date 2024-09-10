document.addEventListener("DOMContentLoaded", function () {
	const createTicketBtnOne = document.getElementById("createTicketButtonOne");
	// const createTicketBtnTwo = document.getElementById("createTicketButtonTwo");
	const closeTicketModalBtn = document.getElementById("modalCloseButton");

	const createTicketContainer = document.getElementById("ticketCreationModal");

	createTicketBtnOne.addEventListener("click", () => {
		createTicketContainer.style.display = "block";
	});

	closeTicketModalBtn.addEventListener("click", () => {
		createTicketContainer.style.display = "none";
	});

	const ticketInfoBtns = document.querySelectorAll(".viewTicketInfoBtn");
	const ticketModals = document.querySelectorAll(".ticketInformationModal");
	const ticketModalCloses = document.querySelectorAll(".ticketInfoModalClose");
	const ticketInfoModalCard = document.querySelectorAll(".ticketInformationCard");

	// Iterate over each button and attach event listeners
	ticketInfoBtns.forEach((btn, index) => {
		btn.addEventListener('click', () => {
			ticketModals[index].style.display = "block";
		});
	});

	ticketModalCloses.forEach((closeBtn, index) => {
		closeBtn.addEventListener('click', () => {
			ticketModals[index].style.display = "none";
		});
	});

	// Optional: Close modal if user clicks outside of the modal
	ticketModals.forEach((modal, index) => {
		modal.addEventListener('click', (event) => {
			const ticketInfoModalCard = modal.querySelector('.ticketInformationCard');
			if (!ticketInfoModalCard.contains(event.target)) {
				modal.style.display = "none";
			}
		});
	});
});
