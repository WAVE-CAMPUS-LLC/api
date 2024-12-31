document.addEventListener("DOMContentLoaded", function () {
  const editButton = document.getElementById("editEventBtn");
  const cancelEdit = document.getElementById("cancelEdit");
  const submitBtn = document.getElementById("submitBtn");

  // "View" elements: shown when not editing
  const viewElements = [
    document.getElementById("eventTitle"),
    document.getElementById("eventType"),
    document.getElementById("eventDate"),
    document.getElementById("eventStartTime"),
    document.getElementById("eventEndTime"),
    document.getElementById("eventDescription"),
    document.getElementById("eventPrivacy"),
    document.getElementById("eventLocation"),
    document.getElementById("bodyImagesTitle"),
    document.getElementById("eventBodyImageOne"),
    document.getElementById("eventBodyImageTwo"),
    document.getElementById("eventBodyImageThree"),
    document.getElementById("eventBodyImageFour"),
    document.getElementById("eventBodyImageFive"),
    // Age Restriction in view mode
    document.getElementById("ageRestrictionView"),
  ].filter(Boolean);

  // "Edit" elements: shown only when editing
  const editElements = [
    document.querySelector(".editEventTitle"),
    document.querySelector(".editEventType"),
    document.querySelector(".editEventDate"),
    document.querySelector(".editEventStartTime"),
    document.querySelector(".editEventEndTime"),
    document.querySelector(".editEventDescription"),
    document.querySelector(".editEventPrivacy"),
    document.querySelector(".editEventBuildingName"),
    document.querySelector(".editEventStreet"),
    document.querySelector(".editEventAptSuit"),
    document.querySelector(".editEventCity"),
    document.querySelector(".editEventState"),
    document.querySelector(".editEventZipCode"),
    document.querySelector(".editEventHeaderPhoto"),
    document.querySelector(".editEventBodyImageOne"),
    document.querySelector(".editEventBodyImageTwo"),
    document.querySelector(".editEventBodyImageThree"),
    document.querySelector(".editEventBodyImageFour"),
    document.querySelector(".editEventBodyImageFive"),
    // Age Restriction in edit mode (the Django radio field)
    document.querySelector(".editEventAgeRestriction"),
  ].filter(Boolean);

  function hideElements(elements) {
    elements.forEach((el) => el.classList.add("hidden"));
  }
  function showElements(elements) {
    elements.forEach((el) => el.classList.remove("hidden"));
  }

  // ----- EDIT BUTTON -----
  editButton.addEventListener("click", function () {
    cancelEdit.classList.remove("hidden");
    editButton.classList.add("hidden");
    submitBtn.classList.remove("hidden");

    hideElements(viewElements);
    showElements(editElements);
  });

  // ----- CANCEL BUTTON -----
  cancelEdit.addEventListener("click", function () {
    cancelEdit.classList.add("hidden");
    editButton.classList.remove("hidden");
    submitBtn.classList.add("hidden");

    showElements(viewElements);
    hideElements(editElements);
  });
});
