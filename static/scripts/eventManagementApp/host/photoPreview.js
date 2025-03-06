document.addEventListener('DOMContentLoaded', function () {
    const headerPhotoInput = document.getElementById("photo-input");
    const headerPhotoPreview = document.getElementById('header-photo-preview');

    if (headerPhotoPreview && headerPhotoPreview.getAttribute('src') && 
        headerPhotoPreview.getAttribute('src') !== '#') {
        headerPhotoPreview.style.display = 'block';
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
    })


    // Body photo preview system
    const fields = [
        'id_body_photo_one',
        'id_body_photo_two',
        'id_body_photo_three',
        'id_body_photo_four',
        'id_body_photo_five'
    ];

    fields.forEach(field => {
        const input = document.getElementById(`${field}`);
        const preview = document.getElementById(`${field}-preview`);

        input.addEventListener('change', function (event) {
            const file = event.target.files[0];
            preview.innerHTML = '';

            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    const image = document.createElement('img');
                    image.src = e.target.result;
                    image.style.maxWidth = '100%';
                    image.style.height = '300px';
                    image.style.borderRadius = '20px';
                    preview.appendChild(image);
                };
                reader.readAsDataURL(file);
            }
        });
    });
})