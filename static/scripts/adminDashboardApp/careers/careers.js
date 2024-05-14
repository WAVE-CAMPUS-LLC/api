document.addEventListener('DOMContentLoaded', function () {
    const viewRoleButton = document.getElementById("expandRoleButton");
    const roleInformationModal = document.getElementById("displayRoleInformation");
    const closeModal = document.getElementById("hideRoleInformationModalButton");

    viewRoleButton.addEventListener('click', function () {
        roleInformationModal.style.display = 'block';
    })

    closeModal.addEventListener('click', function () {
        roleInformationModal.style.display = 'none';
    })
})