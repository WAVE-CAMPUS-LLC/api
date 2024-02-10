document.addEventListener('DOMContentLoaded', function () {
    var pwCardContainer = document.getElementById('pw-card_container');
    var passwordCard = document.getElementById('passwordCard');
    const updatePwForm = document.getElementById('passwordForm');

    // Function to display the password card
    function displayPasswordContainer() {
        pwCardContainer.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Disable background scrolling
    }

    // Function to hide the password card
    function hidePasswordContainer() {
        pwCardContainer.style.display = 'none';
        document.body.style.overflow = ''; // Enable background scrolling
    }

    // Event listener to display the password card
    document.getElementById('updatePwbtn').addEventListener('click', function (event) {
        event.stopPropagation(); // Prevents the click event from reaching the document
        displayPasswordContainer();
    });

    // Hide the password card initially
    pwCardContainer.style.display = 'none';

    // Event listener for clicks outside the card
    document.addEventListener('click', function (event) {
        // Check if the clicked element is outside the password card
        if (!passwordCard.contains(event.target) && event.target.id !== 'updatePwbtn') {
            hidePasswordContainer();
        }
    });

    // Event listener for the "Esc" key
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            hidePasswordContainer();
        }
    });

    updatePwForm.addEventListener('submit', function (event) {
        event.preventDefault();

        var formData = new FormData(updatePwForm);

        fetch('/change-password/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if(data.success){
                hidePasswordContainer();
                alert("Change successful.")
            }
            else {
                alert("Password change unsuccessful.")
            }
        })
        .catch(error => {
            console.error('Error: ', error);
            alert('Error occurred. Try again.')
        });
    });
});

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}