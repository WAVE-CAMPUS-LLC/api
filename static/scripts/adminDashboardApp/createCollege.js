document.addEventListener('DOMContentLoaded', function() {
    const createCollegeBtn = document.getElementById('createCollegeBtn');
    const collegeCreateModal = document.getElementById('createCollegeModal');
    const closeCollegeModal = document.getElementById('closeCreateCollegeModalButton');

    createCollegeBtn.addEventListener('click', function() {
        collegeCreateModal.style.display = 'block';
    });

    closeCollegeModal.addEventListener('click', function() {
        collegeCreateModal.style.display = 'none';
    });
})