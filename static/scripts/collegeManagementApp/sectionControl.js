document.addEventListener('DOMContentLoaded', function () {
    const sections = document.querySelectorAll('.section');
    const nextButton = document.getElementById('nextSectionButton');
    const previousButton = document.getElementById('previousSectionButton');
    const submitButton = document.getElementById('submitButton');
    let currentSectionIndex = 0;

    const apiKey = document.getElementById('apiKey').value;

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
        previousButton.style.display = index === 0 ? 'none' : 'inline-block';
        nextButton.style.display = index === sections.length - 1 ? 'none' : 'inline-block';
        submitButton.style.display = index === sections.length - 1 ? 'inline-block' : 'none';

        validateCurrentSection();
    }

    function validateCurrentSection() {
        const activeSection = sections[currentSectionIndex];
        const input = activeSection.querySelector('input'); 
    
        nextButton.disabled = true; 
        if (input) {
            validateInput(input);

            input.addEventListener('input', () => {
                validateInput(input);
            });
        }
    }
    
    function validateInput(input) {
        const suggestionsBox = document.querySelector('#suggestions-box');
    
        if (input.id === 'id_name') {  // Only for college name input
            const query = input.value.trim();
    
            if (query.length > 0) {
                fetchCollegeSuggestions(query);  
                nextButton.disabled = false;  
                suggestionsBox.classList.add('hide');  
            } else {
                suggestionsBox.classList.remove('hide'); 
                nextButton.disabled = true;  
            }
        } else if (input.type === 'email') { 
            nextButton.disabled = !validateEmail(input.value);  
        } else {
            nextButton.disabled = input.value.trim() === '';
        }
    }

    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(String(email).toLowerCase());
    }

    // Fetch college suggestions from the College Scorecard API
    function fetchCollegeSuggestions(query) {
        const url = `https://api.data.gov/ed/collegescorecard/v1/schools?api_key=${apiKey}&school.name=${query}&fields=id,school.name`;
        const suggestionsBox = document.querySelector('#suggestions-box');

        fetch(url)
            .then(response => response.json())
            .then(data => {
                displaySuggestions(data.results);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });

        function displaySuggestions(schools) {
            suggestionsBox.innerHTML = ''; 

            if (schools.length > 0) {
                schools.forEach(school => {
                    const suggestionItem = document.createElement('div');
                    suggestionItem.textContent = school['school.name'];
                    suggestionItem.classList.add('suggestion-item');

                    suggestionItem.addEventListener('click', () => {
                        document.getElementById('id_name').value = school['school.name'];
                        suggestionsBox.classList.add('hide'); 
                    });

                    suggestionsBox.appendChild(suggestionItem);
                });
            } else {
                suggestionsBox.innerHTML = '<div style="padding: 10px;">Cannot find your University. Check your spelling and try again</div>';
            }
        }
    }

    nextButton.addEventListener('click', () => {
        if (currentSectionIndex < sections.length - 1) {
            currentSectionIndex++;
            showSection(currentSectionIndex);
        }
    });

    previousButton.addEventListener('click', () => {
        nextButton.disabled = false;
        if (currentSectionIndex > 0) {
            currentSectionIndex--;
            showSection(currentSectionIndex);
        }
    });

    showSection(currentSectionIndex);
});
