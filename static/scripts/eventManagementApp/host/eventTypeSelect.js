// let selectedEventType = null;

// function selectEventType(element) {
//     const eventType = element.getAttribute('data-value');

//     // If there is a previously selected event type, deselect it
//     if (selectedEventType) {
//         document.querySelector(`.type-selector[data-value="${selectedEventType}"]`).classList.remove('selected');
//     }

//     // Set the new selected event type
//     selectedEventType = eventType;
//     element.classList.add('selected');

//     console.log('selected types: ', selectedEventType);
// }

let selectedEventType = null;
let selectedPrivacyType = null;

function selectEventType(selectElement) {
    const selectedValue = selectElement.value;

    // Remove 'selected' class from all options
    document.querySelectorAll('.type-selector').forEach((element) => {
        element.classList.remove('selected');
    });

    // Add 'selected' class to the chosen option
    const selectedOption = document.querySelector(`.type-selector[data-value="${selectedValue}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
}

function selectEventTypeOption(value) {
    const selectElement = document.getElementById('event-type-select');
    selectElement.value = value;

    selectEventType(selectElement);
}


function selectPrivacyType(selectElement) {
    const selectedValue = selectElement.value;

    // Remove 'selected' class from all options
    document.querySelectorAll('.privacy-selector').forEach((element) => {
        element.classList.remove('selected');
    });

    // Add 'selected' class to the chosen option
    const selectedOption = document.querySelector(`.privacy-selector[data-value="${selectedValue}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
}

function selectPrivacyTypeOption(value) {
    const selectElement = document.getElementById('privacy-type-select');
    selectElement.value = value;

    selectPrivacyType(selectElement);
}


// Initialize the default selection if any
document.addEventListener('DOMContentLoaded', function () {
    const defaultSelectedValue = document.getElementById('event-type-select').value;
    const defaultPrivacySelectedValue = document.getElementById('privacy-type-select').value;
    if (defaultSelectedValue) {
        selectEventTypeOption(defaultSelectedValue);
    }

    if (defaultPrivacySelectedValue) {
        selectPrivacyTypeOption(defaultPrivacySelectedValue);
    }
});
