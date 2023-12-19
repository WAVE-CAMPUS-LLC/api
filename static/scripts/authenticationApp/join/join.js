const sections = document.querySelectorAll('.section-one, .section-two');
const returnButton = document.getElementById('returnContainer');
const nextButton = document.querySelector('#nextContainer button');
const submitButton = document.querySelector('button[type="submit"]');

let currentSectionIndex = 0;

function showSection(index) {
    sections.forEach((section, idx) => {
        if (idx === index) {
            section.style.display = 'block';
        } else {
            section.style.display = 'none';
        }
    });

    if (index === sections.length - 1) {
        nextButton.style.display = 'none'; // Hide next button on the last section
        submitButton.style.display = 'block'; // Display submit button on the last section
    } else {
        nextButton.style.display = 'block';
        submitButton.style.display = 'none';
    }
}

// Initial setup
showSection(currentSectionIndex);

nextButton.addEventListener('click', () => {
    currentSectionIndex++;
    showSection(currentSectionIndex);
});

returnButton.addEventListener('click', () => {
    if (currentSectionIndex > 0) {
        currentSectionIndex--;
        showSection(currentSectionIndex);
    }
});
