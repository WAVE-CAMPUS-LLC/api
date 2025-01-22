document.addEventListener("DOMContentLoaded", function() {
    // Restrict event type selection to a maximum of 10
    const eventOptions = document.querySelectorAll(".eventTypeSelectorButtons input[type='checkbox']");

    eventOptions.forEach(option => {
        option.addEventListener('change', function() {
            const selectedOptions = document.querySelectorAll('.eventTypeSelectorButtons input[type="checkbox"]:checked');
            if (selectedOptions.length > 10) {
                option.checked = false;
                alert("You can select a maximum of 10 event types.");
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