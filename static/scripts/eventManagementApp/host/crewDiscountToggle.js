document.addEventListener("DOMContentLoaded", function () {
    const toggleSwitch = document.getElementById("id_crew_discount");
    const crewInfoRow = document.getElementById("crewInfoRow");

    // Function to toggle visibility
    function toggleCrewInfoRow() {
        if (toggleSwitch?.checked && crewInfoRow) {
            crewInfoRow.style.display = "grid"; // Show the row    
        } else if (crewInfoRow) {
            crewInfoRow.style.display = "none"; // Hide the row
        }
    }

    // Attach event listener to the checkbox
    toggleSwitch?.addEventListener("change", toggleCrewInfoRow);

    // Set the initial state on page load
    toggleCrewInfoRow();
});
