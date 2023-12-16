const sections = document.querySelectorAll('.section');
const headers = document.querySelectorAll('.sectionh');
const nextButton = document.getElementById('nextButton');
const backButton = document.getElementById('backButton');
const submitButton = document.getElementById('submitButton');
let currentSectionIndex = 0;

function showSection(index) {
    sections.forEach((section, i) => {
        if (i === index) {
            section.classList.add('active');
        } else {
            section.classList.remove('active');
        }
    });

    headers.forEach((header, i) => {
        if (i === index) {
            header.classList.add('active');
        } else {
            header.classList.remove('active');
        }
    });

    if (index === sections.length - 1) {
        nextButton.style.display = 'none';
        submitButton.style.display = 'block';
    } else {
        nextButton.style.display = 'block';
        submitButton.style.display = 'none';
    }

    if (index === 0) {
        backButton.style.display = 'none';
    } else {
        backButton.style.display = 'block';
    }

    if (index === 0) {
        nextButton.classList.add('centered');
    } else {
        nextButton.classList.remove('centered');
    }
}

showSection(currentSectionIndex);

nextButton.addEventListener('click', () => {
    if (currentSectionIndex < sections.length - 1) {
        currentSectionIndex++;
        showSection(currentSectionIndex);
    }
});

backButton.addEventListener('click', () => {
    if (currentSectionIndex > 0) {
        currentSectionIndex--;
        showSection(currentSectionIndex);
    }
});

submitButton.addEventListener('click', () => {
    // Handle form submission logic here
});
