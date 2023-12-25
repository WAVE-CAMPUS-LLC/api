// const sections = document.querySelectorAll('.section-one, .section-two');
// const returnButton = document.getElementById('returnContainer');
// const nextButton = document.querySelector('#nextContainer button');
// const submitButton = document.querySelector('button[type="submit"]');

// let currentSectionIndex = 0;

// function showSection(index) {
//     sections.forEach((section, idx) => {
//         if (idx === index) {
//             section.style.display = 'block';
//         } else {
//             section.style.display = 'none';
//         }
//     });

//     if (index === sections.length - 1) {
//         nextButton.style.display = 'none'; // Hide next button on the last section
//         submitButton.style.display = 'block'; // Display submit button on the last section
//         submitButton.addEventListener('click', () => {
//             document.querySelector('form').submit();
//         });
//     } else {
//         nextButton.style.display = 'block';
//         submitButton.style.display = 'none';
//     }
// }

// // Initial setup
// showSection(currentSectionIndex);

// nextButton.addEventListener('click', () => {
//     currentSectionIndex++;
//     showSection(currentSectionIndex);
// });

// returnButton.addEventListener('click', () => {
//     if (currentSectionIndex > 0) {
//         currentSectionIndex--;
//         showSection(currentSectionIndex);
//     }
// });


const sections = document.querySelectorAll('.section-one, .section-two');
const returnButton = document.getElementById('returnContainer');
const nextButton = document.querySelector('#nextContainer button');
const submitButton = document.querySelector('button[type="submit"]');
const currentSectionInput = document.getElementById('currentSectionIndex');

let currentSectionIndex = parseInt(currentSectionInput.value || 0);

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

    // Update the hidden input field with the current section index
    currentSectionInput.value = index;
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

// Prevent form submission on "Next" button click
nextButton.addEventListener('click', (e) => {
    e.preventDefault();
});

// Form submission on "Submit" button click
submitButton.addEventListener('click', () => {
    document.querySelector('form').submit();
});
