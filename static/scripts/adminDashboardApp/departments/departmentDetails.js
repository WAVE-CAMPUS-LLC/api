document.addEventListener('DOMContentLoaded', function () {
    const editButton = document.getElementById('deptEditButton');
    const saveButton = document.getElementById('deptSaveButton');
    const editSummary = document.getElementById('editSummary');
    const displaySummary = document.getElementById('displaySummary');

    editButton.addEventListener('click', function () {
        editSummary.style.display = 'block';  // Show the edit form
        displaySummary.style.display = 'none';  // Hide the display summary
    });

    saveButton.addEventListener('click', function () {
        // Submit the form
        document.getElementById('departmentForm').submit();
    });
});