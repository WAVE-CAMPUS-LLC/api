document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const nextButton = document.getElementById('nextSectionButton');
    const previousButton = document.getElementById('previousSectionButton');
    const submitButton = document.getElementById('submitButton');
    let currentSectionIndex = 0;

    function showSection(index) {
        sections.forEach((section, i) => {
            if (i === index) {
                section.classList.remove('hidden'); // Show current section
                section.classList.add('block'); // Ensure it's displayed as a block
            } else {
                section.classList.add('hidden'); // Hide other sections
                section.classList.remove('block');
            }
        });

        // Toggle button visibility based on current index
        if (index === 0) {
            previousButton.classList.add('hidden');
            previousButton.classList.remove('flex');
        } else {
            previousButton.classList.remove('hidden');
            previousButton.classList.add('flex');
        }

        if (index === sections.length - 1) {
            nextButton.classList.add('hidden');
            nextButton.classList.remove('flex');
            submitButton.classList.remove('hidden');
            submitButton.classList.add('flex');
        } else {
            nextButton.classList.remove('hidden');
            nextButton.classList.add('flex');
            submitButton.classList.add('hidden');
            submitButton.classList.remove('flex');
        }
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