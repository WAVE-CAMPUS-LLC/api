document.addEventListener('DOMContentLoaded', function () {
    const editButton = document.getElementById('editCollege');
    const displayInfos = document.querySelectorAll('.displayInfo');
    const cancelEditButton = document.getElementById('cancelEditCollege');
    const saveCancel = document.getElementById('saveCancel');
    const editInputs = document.querySelectorAll('.editInput');
    const editInfoDiv = document.getElementById('editInfoDiv');


    editButton.addEventListener('click', function () {
        displayInfos.forEach((displayInfo) => {
            displayInfo.classList.add('hidden');
        });
        editButton.classList.add('hidden');
        cancelEditButton.classList.remove('hidden');
        saveCancel.classList.remove('hidden');
        editInfoDiv.classList.add('hidden');

        editInputs.forEach((editInput) => {
            editInput.classList.remove('hidden');
        });
    });

    cancelEditButton.addEventListener('click', function () {
        displayInfos.forEach((displayInfo) => {
            displayInfo.classList.remove('hidden');
        });
        editButton.classList.remove('hidden');
        cancelEditButton.classList.add('hidden');
        saveCancel.classList.add('hidden');
        editInfoDiv.classList.remove('hidden');

        editInputs.forEach((editInput) => {
            editInput.classList.add('hidden');
        });
    });
});
