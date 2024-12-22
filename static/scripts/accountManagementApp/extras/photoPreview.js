document.addEventListener('DOMContentLoaded', function () {
    const headerPhotoInput = document.getElementById("photo-input");
    const headerPhotoPreview = document.getElementById('header-photo-preview');

    if (!headerPhotoInput || !headerPhotoPreview) {
        console.error("Required elements not found in the DOM.");
        return;
    }

    headerPhotoInput.addEventListener('change', function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                headerPhotoPreview.src = e.target.result;
                headerPhotoPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
});
