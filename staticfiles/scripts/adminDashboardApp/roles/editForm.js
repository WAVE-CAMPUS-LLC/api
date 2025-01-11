document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form[id^="editGroupForm-"]');

    forms.forEach(form => {
        const inputs = form.querySelectorAll('input');
        const updateButton = form.querySelector('.updateGroupButton');

        inputs.forEach(input => {
            input.addEventListener('input', function () {
                checkForChanges(form, updateButton);
            });

            if (input.type === 'checkbox') {
                input.addEventListener('change', function () {
                    checkForChanges(form, updateButton);
                });
            }
        });
    });

    function checkForChanges(form, updateButton) {
        const inputs = form.querySelectorAll('input');
        let hasChanges = false;

        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                if (input.dataset.original !== input.checked.toString()) {
                    hasChanges = true;
                }
            } else {
                if (input.dataset.original !== input.value) {
                    hasChanges = true;
                }
            }
        });

        if (hasChanges) {
            updateButton.style.display = 'block';
        } else {
            updateButton.style.display = 'none';
        }
    }
});
