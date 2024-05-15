document.addEventListener('DOMContentLoaded', function () {
    const applicantCard = document.getElementById("applicantCard");
    const applicantInfoModal = document.getElementById("applicantInfoModal");
    const closeModalBtn = document.getElementById("hideAppModalButton");

    applicantCard.addEventListener('click', function () {
        applicantInfoModal.style.display = 'block';
    })

    closeModalBtn.addEventListener('click', function () {
        applicantInfoModal.style.display = 'none';
    })



})

function setAppAction(action) {
    document.getElementById("applicationAction").value = action;
    document.getElementById("applicationActionForm").submit();
}