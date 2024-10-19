document.addEventListener("DOMContentLoaded", function() {
    // Restrict event type selection to a maximum of 3
    const eventOptions = document.querySelectorAll(".eventTypeSelectorButtons input[type='checkbox']");

    eventOptions.forEach(option => {
        option.addEventListener('change', function() {
            const selectedOptions = document.querySelectorAll('.eventTypeSelectorButtons input[type="checkbox"]:checked');
            if (selectedOptions.length > 10) {
                option.checked = false;
            }
        });
    });


    const optionalsContainers = document.querySelectorAll('.optionals');

    optionalsContainers.forEach(container => {
        const checkbox = container.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', function() {
            if (checkbox.checked) {
                container.classList.add('selected');
            } else {
                container.classList.remove('selected');
            }
        });
    });
    
});