let notificationTimeout = null;

function showNotification(message) {
  const notificationArea = document.getElementById("notificationArea");
  
  // Set the notification message
  notificationArea.innerText = message;
  
  // Remove hidden classes so both overlay and notification show
  notificationArea.classList.remove("hidden");
  
  // If a previous timeout exists, clear it
  if (notificationTimeout !== null) {
    clearTimeout(notificationTimeout);
  }
  
  // Hide the notification and overlay after 3000ms
  notificationTimeout = setTimeout(() => {
    notificationArea.classList.add("hidden");
    notificationTimeout = null;
  }, 1000);
}


document.addEventListener("DOMContentLoaded", function () {
  const favoriteForm = document.getElementById("favoriteEventForm");
  const unFavoriteForm = document.getElementById("unFavoriteEventForm");
  const isFavoriteEvent = document.getElementById("isFavoriteEvent").value;
  const favoriteButton = document.getElementById("favoriteEventButton");
  const unFavoriteButton = document.getElementById("unFavoriteEventButton");
  const eventId = document.getElementById("favoriteEventId").value;

  if (isFavoriteEvent === "True") {
    favoriteForm.style.display = "none";
    unFavoriteForm.style.display = "block";
  } else {
    favoriteForm.style.display = "block";
    unFavoriteForm.style.display = "none";
  }

  favoriteForm.addEventListener("submit", handleSubmit);
  unFavoriteForm.addEventListener("submit", handleSubmit);

  function handleSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    
    const toggleFavoriteURL = `/events/${eventId}/toggle-favorite/`;

    fetch(toggleFavoriteURL, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie("csrftoken")
      }
    })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      console.log("Server response:", data);

      if (data.status === "successfulFavorite") {
        favoriteForm.style.display = "none";
        unFavoriteForm.style.display = "block";
      } else if (data.status === "successfulUnfavorite") {
        favoriteForm.style.display = "block";
        unFavoriteForm.style.display = "none";
      }
      showNotification(data.message);
      form.dataset.submitted = "false";
      favoriteButton.disabled = false;
      unFavoriteButton.disabled = false;

    })
    .catch((error) => {
      console.error("Error submitting form:", error);
      form.dataset.submitted = "false";
      favoriteButton.disabled = false;
      unFavoriteButton.disabled = false;
    });
  }
});
