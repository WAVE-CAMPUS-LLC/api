$(document).ready(function () {
    let currentSectionIndex = 0;
    const sections = $('section#stage-section');
    const saveUrl = document.getElementById('creation-control').dataset.saveUrl;
    const nextButton = $('#next-sectionbtn');

    nextButton.hide();

    function displaySection(index) {
        sections.hide();
        $(sections[index]).show();
        validateCurrentSection();
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

    function validateCurrentSection() {
        const currentSection = $(sections[currentSectionIndex]);
        let isValid = true;

        currentSection.find('input, textarea, select').each(function () {
            if ($(this).prop('required') && !$(this).val()) {
                isValid = false;
            }
        });

        if(currentSectionIndex === 1) {
            currentSection.find('.text-input').each(function () {
                const len = $(this).val().length;
                if (len == 0 ) {
                    $("#title-error").hide();
                } else if (len < 4) {
                    isValid = false;
                    $("#title-error").text("Title needs to be longer.").show();
                } else if (len > 100) {
                    isValid = false;
                    $("#title-error").text("Title needs to be shorter.").show();
                } else {
                    $("#title-error").hide();
                }
            });
        } else if (currentSectionIndex === 3) {
            currentSection.find('.date-input').each(function () {
                const len = $(this).val().length;
                const selectedDate = new Date($(this).val());
                const currentDate = new Date();
                const futureLimitDate = new Date(currentDate);
                
                futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
                currentDate.setHours(-24, 0, 0, 0); 
    
                if (len == 0) {
                    $("#date-error").hide();
                } else if (selectedDate.getTime() < currentDate.getTime()) {
                    isValid = false;
                    $("#date-error").text("Date cannot be in the past.").show();
                } else if (selectedDate.getTime() > futureLimitDate.getTime()) {
                    isValid = false;
                    $("#date-error").text("Date cannot be in more than a year into the future.").show();
                } else {
                    $("#date-error").hide();
                }
            });
        } else if (currentSectionIndex === 4) {
            currentSection.find('.start-time-input').each(function () {
                const startTime = $('.start-time-input').val();
                const endTime = $('.end-time-input').val();
        
                if (startTime.length === 0 || endTime.length === 0) {
                    $("#time-error").hide();
                } else {
                    const today = new Date();
                    const start = new Date(today.toDateString() + ' ' + startTime);
                    let end = new Date(today.toDateString() + ' ' + endTime);
        
                    if (end < start) {
                        end.setHours(end.getHours() + 24);
                    }
        
                    const hourDifference = (end - start) / (1000 * 60 * 60);
        
                    if (hourDifference > 12) {
                        isValid = false;
                        $("#time-error").show();
                    } else {
                        $("#time-error").hide();
                    }
                }
            });
        } else if (currentSectionIndex === 5) {
            currentSection.find('.body-input').each(function () {
                const len = $(this).val().length;
                
                if (len == 0 ) {
                    $("#body-error").hide();
                } else if (len < 10) {
                    isValid = false;
                    $("#body-error").text("Description needs to be longer.").show();
                } else if (len > 5000) {
                    isValid = false;
                    $("#body-error").text("Description needs to be shorter.").show();
                } else {
                    $("#body-error").hide();
                }
            });
        }

        if (isValid) {
            nextButton.show();  
        } else {
            nextButton.hide(); 
        }

        if (currentSectionIndex === sections.length - 1) {
            nextButton.hide(); 
        }
    }

    $('input, textarea, select').on('input change', function () {
        validateCurrentSection(); 
    });
});
