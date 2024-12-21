document.addEventListener("DOMContentLoaded", function () {
  const requestCountElement = document.getElementById("number-of-requests");
  let currentCount = parseInt(
    requestCountElement.getAttribute("data-initial-count")
  );

  if (currentCount == 0) {
    requestCountElement.style.display = "none";
  } else {
    requestCountElement.style.display = "block";
  }

  const socket = new WebSocket(`ws://${window.location.host}/social/`);

  socket.onopen = function () {
    console.log("WebSocket connected for socialHomeView");
  };

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.status == "sent") {
      currentCount += 1;
      requestCountElement.style.display = "block";

      if (currentCount > 9) {
        requestCountElement.textContent = "9+";
      } else {
        requestCountElement.textContent = currentCount;
      }
    } else {
      currentCount -= 1;
      if (currentCount <= 0) {
        requestCountElement.style.display = "none";
      } else {
        requestCountElement.style.display = "block";
        requestCountElement.textContent = currentCount;
      }
    }
  };

  socket.onclose = function () {
    console.log("WebSocket disconnected for socialHomeView");
  };
});
