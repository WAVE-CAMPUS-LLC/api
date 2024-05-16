document.addEventListener("DOMContentLoaded", function () {
    const faqInfoDivs = document.querySelectorAll(".faq-info");

    faqInfoDivs.forEach((faqInfoDiv) => {
        const faqInfoPopup = faqInfoDiv.querySelector(".faqInfo-popup");
        const faqPopupClose = faqInfoDiv.querySelector("#contentCardClose-button");
        const faqPopupContainer = faqInfoDiv.querySelector(".faqIp-container");

        // if (faqPopupClose) {
        //     console.log("Pop close button found.");
        // }

        faqInfoDiv.addEventListener("click", () => {
            faqInfoPopup.style.display = "block";
        });

        faqPopupClose.addEventListener("click", (event) => {
            event.stopPropagation();
            faqInfoPopup.style.display = "none";
        });
    });
    
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            // Hide the card when the escape key is pressed
            faqInfoDivs.forEach((faqInfoDiv) => {
                const faqInfoPopup = faqInfoDiv.querySelector(".faqInfo-popup");
                faqInfoPopup.style.display = "none";
            });
        }
    });
});
