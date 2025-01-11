document.addEventListener("DOMContentLoaded", function () {
    const eventTitleButton = document.getElementById("eventTitleButton");
    const eventTypeButton = document.getElementById("eventTypeButton");
    const eventDateButton = document.getElementById("eventDateButton");
    const eventStartTimeButton = document.getElementById("eventStartTimeButton");
    const eventEndTimeButton = document.getElementById("eventEndTimeButton");
    const eventDescriptionButton = document.getElementById("eventDescriptionButton");
    const eventPrivacyButton = document.getElementById("eventPrivacyButton");
    const eventAddressButton = document.getElementById("eventAddressButton");
    const eventEmailButton = document.getElementById("eventEmailButton");
    const eventPhoneButton = document.getElementById("eventPhoneButton");
    const eventWebsiteButton = document.getElementById("eventWebsiteButton");
    const eventInstagramButton = document.getElementById("eventInstagramButton");

    const closeFormButton = document.getElementById("eventInformationCardClose-button");

    const eventInformationPopup = document.getElementById("eventInformationPopup");
    const eventTitleForm = document.getElementById("eventTitleForm");
    const eventTypeForm = document.getElementById("eventTypeForm");
    const eventDateForm = document.getElementById("eventDateForm");
    const eventStartTimeForm = document.getElementById("eventStartTimeForm");
    const eventEndTimeForm = document.getElementById("eventEndTimeForm");
    const eventDescriptionForm = document.getElementById("eventDescriptionForm");
    const eventPrivacyForm = document.getElementById("eventPrivacyForm");
    const eventAddressForm = document.getElementById("eventAddressForm");
    const eventEmailForm = document.getElementById("eventEmailForm");
    const eventPhoneForm = document.getElementById("eventPhoneForm");
    const eventWebsiteForm = document.getElementById("eventWebsiteForm");
    const eventInstagramForm = document.getElementById("eventInstagramForm");

    closeFormButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "none";
        eventTitleForm.style.display = "none";
        eventTypeForm.style.display = "none";
        eventDateForm.style.display = "none";
        eventStartTimeForm.style.display = "none";
        eventEndTimeForm.style.display = "none";
        eventDescriptionForm.style.display = "none";
        eventPrivacyForm.style.display = "none";
        eventAddressForm.style.display = "none";
        eventEmailForm.style.display = "none";
        eventPhoneForm.style.display = "none";
        eventWebsiteForm.style.display = "none";
        eventInstagramForm.style.display = "none";
    });

    eventTitleButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventTitleForm.style.display = "block";
    });

    eventTypeButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventTypeForm.style.display = "block";
    });

    eventDateButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventDateForm.style.display = "block";
    });

    eventStartTimeButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventStartTimeForm.style.display = "block";
    });

    eventEndTimeButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventEndTimeForm.style.display = "block";
    });

    eventDescriptionButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventDescriptionForm.style.display = "block";
    });

    eventPrivacyButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventPrivacyForm.style.display = "block";
    });

    eventAddressButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventAddressForm.style.display = "block";
    });

    eventEmailButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventEmailForm.style.display = "block";
    });

    eventPhoneButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventPhoneForm.style.display = "block";
    });

    eventWebsiteButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventWebsiteForm.style.display = "block";
    });

    eventInstagramButton.addEventListener("click", () => {
        eventInformationPopup.style.display = "block";
        eventInstagramForm.style.display = "block";
    });
})