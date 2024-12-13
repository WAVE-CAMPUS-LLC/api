document.addEventListener("DOMContentLoaded", function() {
    const formSectorOne = document.getElementById("about-yrslf");
    const formSectorTwo = document.getElementById("about-yrorg");
    const formSectorThree = document.getElementById("about-yrevent");

    const sectorOneNextButton = document.getElementById("nextButtonOne");

    const sectorTwoNextButton = document.getElementById("nextButtonTwo");
    const previousButtonSTwo = document.getElementById("previousButtonyrOrg");

    const previousButtonSThree = document.getElementById("previousButtonyrEvent");

    const wwuListItems = document.querySelectorAll("#work-with-us .wwu-heading ul li");
    const wwuListItemSpan = document.querySelectorAll("#work-with-us .wwu-heading ul li span");

    let currentSectionIndex = 0;


    function highlightListItem(index) {
        wwuListItems.forEach((item, i) => {
            if (i === index) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        wwuListItemSpan.forEach((item, i) => {
            if (i === index) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    }

    sectorOneNextButton.addEventListener('click', function() {
        formSectorOne.style.display = "none";
        formSectorTwo.style.display = 'flex';

        currentSectionIndex++;
        highlightListItem(currentSectionIndex);
    });

    previousButtonSTwo.addEventListener('click', function(){
        formSectorTwo.style.display = "none";
        formSectorOne.style.display = "flex";

        currentSectionIndex--;
        highlightListItem(currentSectionIndex);
    });

    sectorTwoNextButton.addEventListener('click', function(){
        formSectorTwo.style.display = 'none';
        formSectorThree.style.display = 'flex';

        currentSectionIndex++;
        highlightListItem(currentSectionIndex);
    });

    previousButtonSThree.addEventListener('click', function(){
        formSectorThree.style.display = 'none';
        formSectorTwo.style.display = 'flex';

        currentSectionIndex--;
        highlightListItem(currentSectionIndex);
    });

    highlightListItem(currentSectionIndex);


    // Restrict event type selection to a maximum of 3
    const eventOptions = document.querySelectorAll(".eventTypeSelectorButtons input[type='checkbox']");

    eventOptions.forEach(option => {
        option.addEventListener('change', function() {
            const selectedOptions = document.querySelectorAll('.eventTypeSelectorButtons input[type="checkbox"]:checked');
            if (selectedOptions.length > 3) {
                option.checked = false;
            }
        });
    });

    // function validateForm() {
    //     var checkboxes = document.querySelectorAll('input[name="eventTypes"]:checked');
    //     if (checkboxes.length === 0) {
    //         alert("Please select at least one event type.");
    //         return false;
    //     }
    //     return true;
    // }

    // validateForm()


    const optionalsContainers = document.querySelectorAll('.optionals');

    optionalsContainers.forEach(container => {
        const checkbox = container.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', function() {
            if (checkbox.checked) {
                container.classList.add('selected');
            } else {
                container.classList.remove('selected');
            }
        });
    });
    
});


document.querySelector("#hostEventApplication").addEventListener("submit", (e) => {
    const eventTypesField = document.querySelector("[name='eventTypes']");
    if (eventTypesField && eventTypesField.offsetParent === null) {
        e.preventDefault(); // Prevent submission
        alert("Please fill out the event type field."); // Inform the user
        // Optionally make the field visible
        eventTypesField.closest(".hidden").classList.remove("hidden");
    }
});
