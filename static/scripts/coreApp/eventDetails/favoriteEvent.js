document.addEventListener("DOMContentLoaded", function () {
  const favoriteForm = document.getElementById("favoriteEventForm");
  const unFavoriteForm = document.getElementById("unFavoriteEventForm");
  const isFavoriteEvent = document.getElementById("isFavoriteEvent").value;

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

    fetch(window.location.href, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.text())
      .then((data) => {
        console.log("Server response:", data);

        if (formData.get("eventAction") === "favoriteEvent") {
          favoriteForm.style.display = "none";
          unFavoriteForm.style.display = "block";
        } else if (formData.get("eventAction") === "unfavoriteEvent") {
          favoriteForm.style.display = "block";
          unFavoriteForm.style.display = "none";
        }
      })
      .catch((error) => {
        console.error("Error submitting form:", error);
      });
  }
});
