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
        // alert("QR Code Content: " + decodedText);
        // console.log("Decoded QR Code Content:", decodedText);
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

function verifyTicket(ticketData, qrReader) {
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
      let name = "";
      if (data.ticketData) {
        if (data.ticketData.guestFirstName && data.ticketData.guestLastName) {
          name = data.ticketData.guestFirstName + " " + data.ticketData.guestLastName;
        } else if (data.ticketData.userFirstName && data.ticketData.userLastName) {
          name = data.ticketData.userFirstName + " " + data.ticketData.userLastName;
        }
      }

      if (data.valid) {
        const ticketStatus = document.querySelector(".ticket-status-valid");
        ticketStatus.textContent = name + ": Valid";
        ticketStatus.style.display = "block";
      } else {
        const ticketStatus = document.querySelector(".ticket-status-invalid");
        ticketStatus.textContent = name + ": Invalid";
        ticketStatus.style.display = "block";
      }

      // Hide status after a delay, restart scan for next ticket
      setTimeout(() => {
        document.querySelector(".ticket-status-valid").style.display = "none";
        document.querySelector(".ticket-status-invalid").style.display = "none";

        // Stop and restart the scanner
        qrReader.stop().then(() => {
          startQrScan(); // Restart the scanner for the next ticket
        });
      }, 3000); // Adjust delay as needed
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
