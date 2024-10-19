document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const nextButton = document.getElementById('nextSectionButton');
    const previousButton = document.getElementById('previousSectionButton');
    const submitButton = document.getElementById('submitButton');
    let currentSectionIndex = 0;

    function showSection(index) {
        sections.forEach((section, i) => {
            section.classList.toggle('active', i === index);
        });
        previousButton.style.display = index === 0 ? 'none' : 'inline-block';
        nextButton.style.display = index === sections.length - 1 ? 'none' : 'inline-block';
        submitButton.style.display = index === sections.length - 1 ? 'inline-block' : 'none';
    }

    nextButton.addEventListener('click', () => {
        if (currentSectionIndex < sections.length - 1) {
            currentSectionIndex++;
            showSection(currentSectionIndex);
        }
    });

    previousButton.addEventListener('click', () => {
        if (currentSectionIndex > 0) {
            currentSectionIndex--;
            showSection(currentSectionIndex);
        }
    });

    showSection(currentSectionIndex);
})