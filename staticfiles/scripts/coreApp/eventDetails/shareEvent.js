document.addEventListener('DOMContentLoaded', function () {
    const shareButton = document.getElementById('shareEventButton');
    const sharePopup = document.getElementById('shareEventPopup');
    const closePopupButton = document.getElementById('closeShareEventPopup');

    shareButton.addEventListener('click', function () {
        sharePopup.classList.toggle('hidden');
    });

    closePopupButton.addEventListener('click', function () {
        sharePopup.classList.toggle('hidden');
    });
});