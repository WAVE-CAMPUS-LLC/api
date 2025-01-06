document.addEventListener('DOMContentLoaded', function() {
    const editInfoDiv = document.getElementById('editInfoDiv');
    const editButton = document.getElementById('editInfoButton');
    const editingButtonsDiv = document.getElementById('editingButtons');
    const cancelButton = document.getElementById('cancelEdit');
    const displayInfoDiv = document.querySelectorAll('.displayInfo');
    const editInfoContainer = document.querySelectorAll('.editInfo');

    editButton.addEventListener('click', function() {
        editInfoDiv.classList.add('hidden');
        editingButtonsDiv.classList.remove('hidden');
        displayInfoDiv.forEach(function(element) {
            element.classList.add('hidden');
        });
        editInfoContainer.forEach(function(element) {
            element.classList.remove('hidden');
        });
    });

    cancelButton.addEventListener('click', function() {
        editInfoDiv.classList.remove('hidden');
        editingButtonsDiv.classList.add('hidden');
        displayInfoDiv.forEach(function(element) {
            element.classList.remove('hidden');
        });
        editInfoContainer.forEach(function(element) {
            element.classList.add('hidden');
        });
    });
});