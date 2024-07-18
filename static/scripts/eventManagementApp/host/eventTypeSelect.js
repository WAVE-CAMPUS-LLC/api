let selectedEventType = null;

function selectEventType(element) {
    const eventType = element.getAttribute('data-value');

    // If there is a previously selected event type, deselect it
    if (selectedEventType) {
        document.querySelector(`.type-selector[data-value="${selectedEventType}"]`).classList.remove('selected');
    }

    // Set the new selected event type
    selectedEventType = eventType;
    element.classList.add('selected');

    console.log('selected types: ', selectedEventType);
}