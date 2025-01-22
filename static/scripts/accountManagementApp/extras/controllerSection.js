// document.addEventListener('DOMContentLoaded', () => {
//     const sections = document.querySelectorAll('.section');
//     const nextButton = document.getElementById('nextSectionButton');
//     const previousButton = document.getElementById('previousSectionButton');
//     const submitButton = document.getElementById('submitButton');
//     let currentSectionIndex = 0;

//     const toggleVisibility = (element, condition) => {
//         element.style.display = condition ? 'inline-block' : 'none';
//     };

//     const showSection = (index) => {
//         sections.forEach((section, i) => {
//             section.classList.toggle('hidden', i !== index);
//         });
//         toggleVisibility(previousButton, index > 0);
//         toggleVisibility(nextButton, index < sections.length - 1);
//         toggleVisibility(submitButton, index === sections.length - 1);
//         validateCurrentSection();
//     };

//     function getCookie(name) {
//         let cookieValue = null;
//         if (document.cookie && document.cookie !== '') {
//             const cookies = document.cookie.split(';');
//             for (let i = 0; i < cookies.length; i++) {
//                 const cookie = cookies[i].trim();
//                 if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                     cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                     break;
//                 }
//             }
//         }
//         return cookieValue;
//     }

//     function validateCurrentSection() {
//         const currentSection = sections[currentSectionIndex];
//         let isValid = true;

//         currentSection.querySelectorAll('input, textarea, select').forEach((input) => {
//             if (input.required && !input.value) {
//                 isValid = false;
//             }
//         });

//         if (currentSectionIndex === 1) {
//             const titleInput = currentSection.querySelector('.text-input');
//             const titleError = document.getElementById('title-error');
//             if (titleInput) {
//                 const len = titleInput.value.length;
//                 if (len === 0) {
//                     titleError.classList.add('hidden');
//                 } else if (len < 4) {
//                     isValid = false;
//                     titleError.textContent = 'Title needs to be longer.';
//                     titleError.classList.remove('hidden');
//                 } else if (len > 100) {
//                     isValid = false;
//                     titleError.textContent = 'Title needs to be shorter.';
//                     titleError.classList.remove('hidden');
//                 } else {
//                     titleError.classList.add('hidden');
//                 }
//             }
//         }

//         toggleVisibility(nextButton, isValid && currentSectionIndex < sections.length - 1);
//     }

//     const sendAjaxUpdate = () => {
//         return new Promise((resolve, reject) => {
//             const formData = new FormData(document.getElementById('profilePreferencesForm'));
//             formData.append('username', '{{ user.username }}');

//             const url = document.getElementById('profilePreferencesForm').dataset.saveUrl;

//             $.ajax({
//                 url: url,
//                 type: 'POST',
//                 headers: {
//                     'X-CSRFToken': getCookie('csrftoken'),
//                 },
//                 data: formData,
//                 processData: false,
//                 contentType: false,
//                 success: (response) => {
//                     if (response.success) {
//                         console.log('Section saved successfully');
//                         resolve(response);
//                     } else {
//                         reject(new Error(response.message || 'Failed to save section data.'));
//                     }
//                 },
//                 error: (error) => {
//                     reject(new Error(error.statusText || 'AJAX request failed.'));
//                 }
//             });
//         });
//     };

//     const navigateSection = (direction) => {
//         const newIndex = currentSectionIndex + direction;

//         if (newIndex >= 0 && newIndex < sections.length) {
//             // Wait for AJAX to complete before navigating
//             sendAjaxUpdate().then(() => {
//                 currentSectionIndex = newIndex;
//                 showSection(currentSectionIndex);
//             }).catch((error) => {
//                 console.error('Error while saving data:', error);
//                 alert('Failed to save section data. Please try again.');
//             });
//         }
//     };

//     nextButton.addEventListener('click', () => navigateSection(1));
//     previousButton.addEventListener('click', () => navigateSection(-1));

//     showSection(currentSectionIndex);
// });
