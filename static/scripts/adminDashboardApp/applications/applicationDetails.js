document.addEventListener('DOMContentLoaded', function() {
    const applicantCard = document.querySelectorAll("#applicant-card");

    applicantCard.forEach((card, index) => {
        const modal = document.getElementById(`viewHostApplicationModal-${index + 1}`);
        card.addEventListener('click', function () {
            modal.style.display = 'block';
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                modal.style.display = 'none';
            }
        });
    });

    // applicantCard.addEventListener('click', function() {
    //     applicationModal.style.display = 'block';        
    // });

    // document.addEventListener('keydown', (event) => {
    //     if (event.key == "Escape") {
    //         applicationModal.style.display = 'none';
    //     }
    // });

    // window.addEventListener('click', function (eventAction) {
    //     if (eventAction.target == applicationModal) {
    //         applicationModal.style.display = 'none';
    //     }
    // })
})