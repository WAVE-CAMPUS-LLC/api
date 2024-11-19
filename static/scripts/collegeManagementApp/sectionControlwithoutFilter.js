document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const nextButton = document.getElementById('nextSectionButton');
    const previousButton = document.getElementById('previousSectionButton');
    const submitButton = document.getElementById('submitButton');
    let currentSectionIndex = 0;

    function showSection(index) {
        sections.forEach((section, i) => {
            if (i === index) {
                section.classList.add('active');
                section.classList.remove('hide');
            } else {
                section.classList.remove('active');
                section.classList.add('hide');
            }
        });

        // Update button visibility
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