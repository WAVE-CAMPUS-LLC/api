document.addEventListener('DOMContentLoaded', () => {
    const sections = document.querySelectorAll('.section');
    const nextButton = document.getElementById('nextSectionButton');
    const previousButton = document.getElementById('previousSectionButton');
    const submitButton = document.getElementById('submitButton');
    let currentSectionIndex = 0;

    const toggleVisibility = (element, condition) => {
        element.style.display = condition ? 'inline-block' : 'none';
    };

    const showSection = (index) => {
        sections.forEach((section, i) => {
            section.classList.toggle('hidden', i !== index);
        });
        toggleVisibility(previousButton, index > 0);
        toggleVisibility(nextButton, index < sections.length - 1);
        toggleVisibility(submitButton, index === sections.length - 1);
    };

    const navigateSection = (direction) => {
        const newIndex = currentSectionIndex + direction;
        if (newIndex >= 0 && newIndex < sections.length) {
            currentSectionIndex = newIndex;
            showSection(currentSectionIndex);
        }
    };

    nextButton.addEventListener('click', () => navigateSection(1));
    previousButton.addEventListener('click', () => navigateSection(-1));

    showSection(currentSectionIndex);
});
