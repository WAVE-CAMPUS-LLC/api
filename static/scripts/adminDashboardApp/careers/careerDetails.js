document.addEventListener('DOMContentLoaded', function () {
    /* This code snippet is selecting all elements with the class name "applicantCard" using
    `document.querySelectorAll(".applicantCard")`. It then iterates over each of these elements
    using `forEach`, passing in the `card` and `index` parameters. */
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

    /* This code snippet is handling the click event on the document. When a click event occurs, it
    checks the target element of the event. If the target element has a class of
    "applicantInfoModal", it extracts the index from the modal's ID and calls the `hideModal`
    function passing in the extracted index to hide that specific modal. */
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

    /**
     * The JavaScript code defines functions to close modals by hiding them based on their index.
     * @param index - The `index` parameter in this context refers to the unique identifier of a
     * specific modal element. It is used to target and hide a modal with the corresponding index in
     * the `hideModal` function.
     */
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