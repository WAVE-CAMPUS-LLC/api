document.addEventListener('DOMContentLoaded', function () {
    const editButton = document.getElementById('deptEditButton');
    const saveButton = document.getElementById('deptSaveButton');
    const editSummary = document.getElementById('editSummary');
    const displaySummary = document.getElementById('displaySummary');

    editButton.addEventListener('click', function () {
        editSummary.style.display = 'block';  // Show the edit form
        displaySummary.style.display = 'none';  // Hide the display summary
        editButton.style.display = 'none';
    });

    saveButton.addEventListener('click', function () {
        // Submit the form
        document.getElementById('departmentForm').submit();
    });


    const roleDisplayCards = document.querySelectorAll(".roleDisplayCard");

    roleDisplayCards.forEach(card => {
        card.addEventListener('click', function () {
            const roleId = card.dataset.roleId;
            const roleDisplayModal = document.getElementById(`roleDisplayModal${roleId}`);

            if (roleDisplayModal) {
                roleDisplayModal.style.display = 'block';
            }
        });
    });


    const roleDisplayCardClose = document.querySelectorAll("#hideModalButton");

    roleDisplayCardClose.forEach(button => {
        button.addEventListener('click', function () {
            const modal = button.closest('.roleDisplayModal');
            modal.style.display = 'none';
        });
    });

    const createNewRoleButton = document.getElementById("createNewRoleButton");
    const createNewRoleModal = document.getElementById("createNewRoleModal");
    const closeCreateNewModalButton = document.getElementById("closeCreateNewRoleModal");

    createNewRoleButton.addEventListener('click', function () {
        createNewRoleModal.style.display = 'block';
    });

    closeCreateNewModalButton.addEventListener('click', function () {
        createNewRoleModal.style.display = 'none';
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modals = document.querySelectorAll('.roleDisplayModal');
            modals.forEach(modal => {
                modal.style.display = 'none';
            });
            createNewRoleModal.style.display = 'none';
        }
    });
});
