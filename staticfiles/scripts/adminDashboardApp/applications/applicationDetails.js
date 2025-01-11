document.addEventListener('DOMContentLoaded', function() {
    const applicantCard = document.querySelectorAll(".applicant-card");

    /* The code snippet you provided is iterating over each `applicantCard` element in the NodeList
    obtained by selecting elements with the id "applicant-card". For each card, it does the
    following: */
    applicantCard.forEach((card, index) => {
        const modal = document.getElementById(`viewHostApplicationModal-${index + 1}`);
        card.addEventListener('click', function () {
            modal.classList.remove('hidden');
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                modal.classList.add('hidden');
            }
        });
    });

    /* The code snippet is selecting all elements with the id "hideModalButton" using
    `document.querySelectorAll("#hideModalButton")` and storing them in the constant `closeModal`. */
    const closeModal = document.querySelectorAll("#hideModalButton");

    closeModal.forEach((button, index) => {
        button.addEventListener('click', function () {
            const modal = document.getElementById(`viewHostApplicationModal-${index + 1}`);
            modal.classList.add('hidden');
        })
    })
})