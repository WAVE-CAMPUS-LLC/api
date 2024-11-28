document.addEventListener("DOMContentLoaded", function () {
  // delete event items
  const deleteEvent = document.getElementById("delete-event");
  const cancelDelete = document.getElementById("cancel-delete-event");
  const confirmDelete = document.getElementById("confirm-delete-event");
  const deleteEventText = document.getElementById("delete-event-description");

  const allEditButtons = document.querySelectorAll(".edit-event");
  allEditButtons.forEach((editButton) => {
    editButton.addEventListener("click", function () {
      const id = editButton.getAttribute("id");
      editField(id, allEditButtons);
    });
  });

  // delete event
  deleteEvent.addEventListener("click", function () {
    deleteEvent.style.display = "none";
    cancelDelete.style.display = "flex";
    confirmDelete.style.display = "flex";
    deleteEventText.style.display = "flex";
  });

  cancelDelete.addEventListener("click", function () {
    deleteEvent.style.display = "flex";
    cancelDelete.style.display = "none";
    confirmDelete.style.display = "none";
    deleteEventText.style.display = "none";
  });
});

function editField(id, allEditButtons) {
  const fieldElement = document.getElementById(id);
  const fieldForm = document.getElementById(`${id}-form`);
  const fieldLabel = document.getElementById(`${id}-previous`);
  const fieldValue = document.getElementById(`${id}-previous-value`);

  fieldElement.style.display = "none";
  fieldLabel.style.display = "none";
  fieldValue.style.display = "none";
  fieldForm.style.display = "block";

  allEditButtons.forEach((editButton) => {
    editButton.style.display = "none";
  });
}
