document.addEventListener('DOMContentLoaded', function() {
    const editCampusButtonRow = document.getElementById('editCampusButtonRow');
    const editCampusButton = document.getElementById('editCampusButton');
    const saveCancelRow = document.getElementById('saveCancelRow');
    const cancelEditButton = document.getElementById('cancelEditButton');
    const displayInfo = document.querySelectorAll('.display-info');
    const editInfo = document.querySelectorAll('.edit-info');


    editCampusButton.addEventListener('click', function() {
        editCampusButtonRow.classList.add('hidden');
        saveCancelRow.classList.remove('hidden');
        displayInfo.forEach(function(info) {
            info.classList.add('hidden');
        });
        editInfo.forEach(function(info) {
            info.classList.remove('hidden');
        });
    });

    cancelEditButton.addEventListener('click', function() {
        editCampusButtonRow.classList.remove('hidden');
        saveCancelRow.classList.add('hidden');
        displayInfo.forEach(function(info) {
            info.classList.remove('hidden');
        });
        editInfo.forEach(function(info) {
            info.classList.add('hidden');
        });
    });
});