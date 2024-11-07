const startButton = document.getElementById("startScanningButton");
const saveUrl = document.getElementById("qrReader").dataset.saveUrl;

startButton.addEventListener("click", function () {
  startScanning();
});

function startScanning() {
  document.getElementById("scanner-container").style.display = "none";
  document.getElementById("scanner-display").style.display = "block";

  startQrScan();
}

function startQrScan() {
  const qrReader = new Html5Qrcode("qrReader");

  // Dynamically calculate qrbox size based on screen width
  const screenWidth = window.innerWidth;
  let qrBoxSize = 250;

  // if (screenWidth < 600) {
  //     qrBoxSize = screenWidth * 0.6; // 60% of the screen width for smaller devices
  // } else if (screenWidth < 1024) {
  //     qrBoxSize = screenWidth * 0.4; // 40% for tablets
  // } else {
  //     qrBoxSize = 250; // Default size for larger screens
  // }

  const config = { fps: 10, qrbox: qrBoxSize };

  qrReader
    .start(
      { facingMode: "environment" },
      config,
      (decodedText, decodedResult) => {
        alert("QR Code Content: " + decodedText);
        verifyTicket(decodedText);
      },
      (errorMessage) => {
        console.log(errorMessage);
      }
    )
    .catch((err) => {
      console.error("Camera initialization error:", err);
    });
}

function verifyTicket(ticketData) {
  const ticketObject = JSON.parse(ticketData);

  if (!ticketObject.ticketId || !ticketObject.eventId || !ticketObject.status) {
    console.error("Ticket data is missing required fields.");
    return;
  }

  fetch(saveUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify(ticketObject),
  })
    .then((response) => response.json())
    .then((data) => {
      const name = "";
      if (data.ticketData.userFirstName) {
        name = data.ticketData.userFirstName;
      } else {
        name = data.ticketData.guestFirstName;
      }
      console.log(data.ticketData);
      if (data.valid) {
        const ticketStatus = document.querySelector(".ticket-status.valid");
        ticketStatus.style.display = "block";
        ticketStatus.textContent = name + ": Valid";
      } else {
        const ticketStatus = document.querySelector(".ticket-status.invalid");
        ticketStatus.style.display = "block";
        ticketStatus.textContent = name + ": Invalid";
      }
    })
    .catch((error) => {
      console.error("Error verifying ticket:", error);
    });
}

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
