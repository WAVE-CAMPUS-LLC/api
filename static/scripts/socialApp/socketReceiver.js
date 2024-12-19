/* This JavaScript code snippet is setting up a WebSocket connection to a server endpoint and updating
the content of an HTML element based on the incoming WebSocket messages. */
document.addEventListener("DOMContentLoaded", function () {
  // Initialize count from the data attribute
  const requestCountElement = document.getElementById("number-of-requests");
  let currentCount = parseInt(
    requestCountElement.getAttribute("data-initial-count")
  );

  const socket = new WebSocket(`ws://${window.location.host}/social/`);

  socket.onopen = function () {
    console.log("WebSocket connected for socialHomeView");
  };

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    console.log(data);
    console.log(data.message);
    console.log("Message received from server");

    currentCount += 1;

    if (currentCount > 9) {
      requestCountElement.textContent = "9+";
    } else {
      requestCountElement.textContent = currentCount;
    }
  };

  socket.onclose = function () {
    console.log("WebSocket disconnected for socialHomeView");
  };
});
