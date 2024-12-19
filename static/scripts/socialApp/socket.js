document.addEventListener("DOMContentLoaded", function () {
  const username = document.getElementById("socketUsername").value;

  const socket = new WebSocket(
    `ws://${window.location.host}/profile/${username}/`
  );

  socket.onopen = function () {
    console.log("WebSocket connected for friend requests");
  };

  socket.onclose = function () {
    console.log("WebSocket disconnected for friend requests");
  };
});
