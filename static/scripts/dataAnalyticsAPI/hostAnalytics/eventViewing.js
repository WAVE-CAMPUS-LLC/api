let viewStartTime;
document.addEventListener("DOMContentLoaded", async function () {
  window.addEventListener("load", () => {
    viewStartTime = Date.now();
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        // Check if this cookie string begins with the name we want
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  window.addEventListener("beforeunload", () => {
    const viewEndTime = Date.now();
    const viewDuration = (viewEndTime - viewStartTime) / 100;

    const fetchUrl = document.getElementById("trackEventViewURL").value;

    fetch(fetchUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({
        event_id: eventId,
        interaction_type: "Viewed",
        duration: viewDuration,
      }),
    }).catch((error) => console.error("Error tracking view:", error));
  });
});
