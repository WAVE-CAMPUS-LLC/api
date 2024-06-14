document.addEventListener('DOMContentLoaded', function () {
    const addRoleToUserButton = document.getElementById("addRoleButton");
    const addRoleCard = document.getElementById("addRoleCardContainer");
    const closeAddRoleCard = document.getElementById("closeAddRoleCardButton");

    addRoleToUserButton.addEventListener('click', function () {
        addRoleCard.style.display = 'block';
    });

    closeAddRoleCard.addEventListener('click', function () {
        addRoleCard.style.display = 'none';
    });


    const suspendButton = document.getElementById("pause");
    const suspendModal = document.getElementById("suspendPeriodModal");

    suspendButton.addEventListener('click', function () {
        suspendModal.style.display = 'block';
    });


    const banButton = document.getElementById("ban");
    const banModal = document.getElementById("banPeriodModal");

    banButton.addEventListener('click', function () {
        banModal.style.display = 'block';
    });


    // Close the suspend or ban card
    const closeSuspendModalButton = document.getElementById("closeSuspendModalButton");
    const closeBanModalButton = document.getElementById("closeBanModalButton");

    closeBanModalButton.addEventListener('click', function() {
        banModal.style.display = 'none';
    });

    closeSuspendModalButton.addEventListener('click', function() {
        suspendModal.style.display = 'none';
    });
})