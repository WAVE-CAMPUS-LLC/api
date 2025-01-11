document.addEventListener('DOMContentLoaded', function () {
    const newDeptButton = document.getElementById("newDepartmentButton");
    const newDeptModal = document.getElementById("newDepartmentModal");
    const closeModalButton = document.getElementById("modalCloseButton");


    newDeptButton.addEventListener('click', function() {
        newDeptModal.style.display = 'block';
    });

    closeModalButton.addEventListener("click", function() {
        newDeptModal.style.display = 'none';
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            newDeptModal.style.display = "none";
        }
    });

    window.addEventListener('click', function (eventAction) {
        if (eventAction.target == newDeptModal) {
            newDeptModal.style.display = 'none';
        }        
    });
})