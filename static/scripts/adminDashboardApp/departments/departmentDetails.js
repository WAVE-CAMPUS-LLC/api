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
    const roleDisplayModal = document.getElementById("roleDisplayModal");
    const roleDisplayCardClose = document.getElementById("closeModalButton");

    roleDisplayCards.forEach(card => {
        card.addEventListener('click', function () {
            roleDisplayModal.style.display = 'block';
        });
    });

    roleDisplayCardClose.addEventListener('click', function () {
        roleDisplayModal.style.display = 'none';
    });


    const createNewRoleButton = document.getElementById("createNewRoleButton");
    const createNewRoleModal = document.getElementById("createNewRoleModal");
    const closeCreateNewModalButton = document.getElementById("closeCreateNewRoleModal");

    createNewRoleButton.addEventListener('click', function() {
        createNewRoleModal.style.display = 'block';
    })

    closeCreateNewModalButton.addEventListener('click', function() {
        createNewRoleModal.style.display = 'none';
    })


    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            roleDisplayModal.style.display = 'none';
            createNewRoleModal.style.display = 'none';
        }
    })
});