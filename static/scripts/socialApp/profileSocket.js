document.addEventListener("DOMContentLoaded", function () {
  const username = document.getElementById("socketUsername").value;

  const socket = new WebSocket(
    `ws://${window.location.host}/profile/${username}/`
  );

  socket.onopen = function () {
    console.log("WebSocket connected for friend requests");
  };

  socket.onclose = function () {
    console.log("WebSocket closed for crew requests");

    // Create the overlay
    const overlay = document.createElement("div");
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    overlay.style.display = "flex";
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.zIndex = "9999";

    // Create the pop-up container
    const popup = document.createElement("div");
    popup.style.position = "relative";
    popup.style.width = "400px";
    popup.style.backgroundColor = "#fff";
    popup.style.borderRadius = "10px";
    popup.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.2)";
    popup.style.padding = "20px";
    popup.style.textAlign = "center";

    // Create the close button
    const closeButton = document.createElement("button");
    closeButton.innerHTML = "&times;";
    closeButton.style.position = "absolute";
    closeButton.style.top = "10px";
    closeButton.style.right = "10px";
    closeButton.style.border = "none";
    closeButton.style.background = "none";
    closeButton.style.fontSize = "20px";
    closeButton.style.cursor = "pointer";

    // Add close functionality
    closeButton.onclick = function () {
      document.body.removeChild(overlay);
    };

    // Add content to the pop-up
    popup.innerHTML = `
      <h4><strong>Live Updates are off!</strong></h4>
    `;
    popup.appendChild(closeButton);

    // Add pop-up to the overlay
    overlay.appendChild(popup);

    // Append the overlay to the body
    document.body.appendChild(overlay);
  };

  socket.onmessage = function (event) {
    location.reload();
  };
});
