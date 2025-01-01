document.addEventListener("DOMContentLoaded", function () {
  const crew_id = document.getElementById("crew_id_socket").value;

  const socket = new WebSocket(
    `ws://${window.location.host}/social/crew/${crew_id}/`
  );

  socket.onopen = function () {
    console.log("WebSocket connected for crew requests");
  };

  socket.onmessage = function () {
    location.reload();
  };
});
