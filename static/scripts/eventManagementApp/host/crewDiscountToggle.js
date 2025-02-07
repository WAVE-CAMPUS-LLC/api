document.addEventListener("DOMContentLoaded", function () {
    const toggleSwitch = document.getElementById("id_crew_discount");
    const crewInfoRow = document.getElementById("crewInfoRow");

    // Function to toggle visibility
    function toggleCrewInfoRow() {
        if (toggleSwitch?.checked) {
            crewInfoRow?.style.display = "grid"; // Display the row
        } else {
            crewInfoRow?.style.display = "none"; // Hide the row
        }
    }

    // Attach event listener to the checkbox
    toggleSwitch?.addEventListener("change", toggleCrewInfoRow);

    // Set the initial state on page load
    toggleCrewInfoRow();
});
