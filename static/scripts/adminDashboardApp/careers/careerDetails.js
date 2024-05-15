document.addEventListener('DOMContentLoaded', function () {
    const applicantCards = document.querySelectorAll(".applicantCard");

    applicantCards.forEach((card, index) => {
        card.addEventListener('click', function () {
            const modal = document.getElementById(`applicantInfoModal-${index + 1}`);
            modal.style.display = 'block';
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                const modal = document.getElementById(`applicantInfoModal-${index + 1}`);
                modal.style.display = 'none';
            }
        });
    });

    document.addEventListener('click', function (event) {
        const target = event.target;
        const modal = target.closest('.applicantInfoModal');
        if (modal) {
            const modalId = modal.id;
            if (modalId) {
                const modalIndex = modalId.split("-")[1];
                hideModal(modalIndex);
            }
        } else {
            const modalContent = target.closest('.applicantInfoModalCard');
            if (!modalContent) {
                const openModals = document.querySelectorAll(".applicantInfoModal.show");
                if (openModals.length > 0) {
                    const modalIndex = openModals[openModals.length - 1].id.split("-")[1];
                    hideModal(modalIndex);
                }
            }
        }
    });

    const closeModalButtons = document.querySelectorAll(".hideAppModalButton");

    closeModalButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const modalIndex = this.id.split("-")[1]; // Extract the index from the button ID
            const modal = document.getElementById(`applicantInfoModal-${modalIndex}`);
            modal.style.display = 'none';
        });
    });

    function hideModal(index) {
        const modal = document.getElementById(`applicantInfoModal-${index}`);
        if (modal) {
            modal.style.display = 'none';
        }
    }


})