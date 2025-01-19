document.addEventListener("DOMContentLoaded", function() {
    const chooseCrewButton = document.getElementById("chooseCrewButton");
    const chooseCrewPopup = document.getElementById("chooseCrewPopup");
    const selectThisCrewButtons = document.querySelectorAll("#selectThisCrewButton");

    chooseCrewButton.addEventListener("click", function() {
        chooseCrewPopup.classList.remove("hidden");
    });

    const closeChooseCrewPopup = document.getElementById("closeChooseCrewPopup");
    closeChooseCrewPopup.addEventListener("click", function() {
        chooseCrewPopup.classList.add("hidden");
    });

    selectThisCrewButtons.forEach(button => {
        button.addEventListener("click", function() {
            const crewId = this.getAttribute("data-crew-id");
            const crewName = this.getAttribute("data-crew-name");
            // Trigger the purchase process for the selected crew
            initiateCrewPurchase(crewId, crewName);
        });
    });

    function initiateCrewPurchase(crewId, crewName) {
        // Logic to initiate the purchase process for the selected crew
        console.log(`Initiating purchase for crew: ${crewName} (ID: ${crewId})`);
        // You can add AJAX calls here to communicate with the backend
    }
});