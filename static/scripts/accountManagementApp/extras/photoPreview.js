document.addEventListener('DOMContentLoaded', function () {
    const headerPhotoInput = document.getElementById("id_profile_photo");
    const headerPhotoPreview = document.getElementById('profile-picture-preview');
    const profileUploadBtn = document.getElementById('profile-picture-upload-btn');

    headerPhotoInput.addEventListener('change', function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                headerPhotoPreview.src = e.target.result;
                headerPhotoPreview.style.display = 'block';
                profileUploadBtn.style.display = 'none';
            };
            reader.readAsDataURL(file);
        }
    })
})