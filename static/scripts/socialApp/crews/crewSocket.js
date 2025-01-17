document.addEventListener("DOMContentLoaded", function () {
  const crew_id = document.getElementById("crew_id_socket").value;

  const socket = new WebSocket(
    `wss://${window.location.host}/social/crew/${crew_id}/`
  );

  socket.onopen = function () {
    console.log("WebSocket connected for crew requests");
  };

  socket.onclose = function () {
    console.log("WebSocket closed for crew requests");

    // 1) Create the HTML for your overlay + popup
    const overlayHTML = `
      <div id="crew-updates-overlay" class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-[9999]">
        <div class="relative w-[400px] bg-white rounded-[10px] shadow-lg p-[20px] text-center">
          <button id="closeOverlayBtn" 
                  class="absolute top-[10px] right-[10px] text-2xl border-none bg-none cursor-pointer">
            &times;
          </button>
              <h4><strong>Live Updates are off!</strong></h4>
        </div>
      </div>
    `;

    // 2) Insert this HTML into the DOM
    document.body.insertAdjacentHTML("beforeend", overlayHTML);

    // 3) Attach close functionality to the button
    document.getElementById("closeOverlayBtn").onclick = function () {
      document.getElementById("crew-updates-overlay").remove();
    };
  };

  socket.onmessage = function () {
    location.reload();
  };
});
