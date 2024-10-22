$(document).ready(function () {
    let currentSectionIndex = 0;
    const sections = $('section#stage-section');
    const saveUrl = document.getElementById('creation-control').dataset.saveUrl;
    const nextButton = $('#next-sectionbtn');


    function displaySection(index) {
        sections.hide();
        $(sections[index]).show();
    }

    displaySection(currentSectionIndex);

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Check if this cookie string begins with the name we want
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    nextButton.click(function () {
        saveFormData()
    });

    // Handle click on the "Previous" button
    $('#previous-sectionbtn').click(function () {
        saveFormData(function () {
            if (currentSectionIndex > 0) {
                currentSectionIndex--;
                displaySection(currentSectionIndex);
            }
        });
    });

    function saveFormData(callback) {
        const formData = new FormData(document.getElementById('eventForm'));
        formData.append('event_id', '{{ event.eventId }}');

        $.ajax({
            url: saveUrl,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function (response) {
                if (callback) {
                    callback();
                } else {
                    if (currentSectionIndex < sections.length - 1) {
                        currentSectionIndex++;
                        displaySection(currentSectionIndex);
                    }
                }
            },
            error: function (xhr, status, error) {
                console.error('Failed to save progress', xhr.responseJSON);
            }
        });
    }
});
