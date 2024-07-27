document.addEventListener('DOMContentLoaded', function () {
    const headerPhotoInput = document.getElementById("id_logo");
    const headerPhotoPreview = document.getElementById('logo-preview');

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
})