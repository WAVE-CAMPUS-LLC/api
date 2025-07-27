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
        verifyUniversalQRCode(decodedText, qrReader);
      },
      (errorMessage) => {
        console.log(errorMessage);
      }
    )
    .catch((err) => {
      console.error("Camera initialization error:", err);
    });
}

function verifyUniversalQRCode(qrCodeData, qrReader) {
  // Universal QR codes contain only the UUID string
  const universalQRCode = qrCodeData.trim();
  const eventId = getEventIdFromPage();

  console.log(
    `Verifying universal QR code: ${universalQRCode} for event: ${eventId}`
  );

  if (!universalQRCode || !eventId) {
    console.error("QR code data or event ID is missing.");
    showError("Invalid QR code or event not specified.");
    return;
  }

  // Use the universal QR verification endpoint
  fetch("/api/ticketing/verify_universal_qr_code/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      qr_code_data: universalQRCode,
      event_id: eventId,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      let name = "Unknown";

      // Extract user name from response
      if (data.user) {
        name =
          `${data.user.first_name || ""} ${data.user.last_name || ""}`.trim() ||
          data.user.username;
      }

      if (data.valid) {
        showSuccess(`${name}: Valid ✅`);
        console.log(`Successfully verified QR code for user: ${name}`);
      } else {
        showError(`${name}: ${data.message || "Invalid"} ❌`);
        console.log(`QR code verification failed: ${data.message}`);
      }

      // Restart scanner after delay
      restartScannerAfterDelay(qrReader);
    })
    .catch((error) => {
      console.error("Error verifying universal QR code:", error);
      showError("Error scanning QR code ❌");
      restartScannerAfterDelay(qrReader);
    });
}

function showSuccess(message) {
  const ticketStatus = document.querySelector(".ticket-status-valid");
  if (ticketStatus) {
    ticketStatus.textContent = message;
    ticketStatus.style.display = "block";
  }
}

function showError(message) {
  const ticketStatus = document.querySelector(".ticket-status-invalid");
  if (ticketStatus) {
    ticketStatus.textContent = message;
    ticketStatus.style.display = "block";
  }
}

function restartScannerAfterDelay(qrReader) {
  setTimeout(() => {
    // Hide status messages
    const validStatus = document.querySelector(".ticket-status-valid");
    const invalidStatus = document.querySelector(".ticket-status-invalid");

    if (validStatus) validStatus.style.display = "none";
    if (invalidStatus) invalidStatus.style.display = "none";

    // Stop and restart the scanner
    if (qrReader && qrReader.stop) {
      qrReader
        .stop()
        .then(() => {
          startQrScan(); // Restart the scanner for the next ticket
        })
        .catch(() => {
          startQrScan(); // Restart even if stop fails
        });
    } else {
      startQrScan(); // Restart the scanner for the next ticket
    }
  }, 3000); // Adjust delay as needed
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

// Helper function to get event ID from the current page
function getEventIdFromPage() {
  // Try to get event ID from URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  let eventId = urlParams.get("eventId") || urlParams.get("event_id");

  if (eventId) {
    console.log(`Found event ID in URL parameters: ${eventId}`);
    return eventId;
  }

  // Try to get from page data attributes
  const eventElement = document.querySelector("[data-event-id]");
  if (eventElement) {
    eventId = eventElement.getAttribute("data-event-id");
    console.log(`Found event ID in data attribute: ${eventId}`);
    return eventId;
  }

  // Try to get from form or hidden input
  const hiddenInput = document.querySelector(
    'input[name="eventId"], input[name="event_id"]'
  );
  if (hiddenInput && hiddenInput.value) {
    eventId = hiddenInput.value;
    console.log(`Found event ID in hidden input: ${eventId}`);
    return eventId;
  }

  // Try to get from global JavaScript variables
  if (typeof window.eventId !== "undefined" && window.eventId) {
    console.log(`Found event ID in window.eventId: ${window.eventId}`);
    return window.eventId;
  }

  // Try to extract from current URL path (e.g., /events/scan/EVENT_ID/)
  const pathParts = window.location.pathname.split("/");
  for (let i = 0; i < pathParts.length; i++) {
    if (pathParts[i] === "scan" && i + 1 < pathParts.length) {
      eventId = pathParts[i + 1];
      if (eventId && eventId !== "") {
        console.log(`Found event ID in URL path: ${eventId}`);
        return eventId;
      }
    }
  }

  // Fallback: prompt user for event ID
  console.warn("Event ID not found on page. Prompting user.");
  eventId = prompt("Please enter the Event ID for this scanning session:");

  if (eventId) {
    console.log(`User provided event ID: ${eventId}`);
    return eventId;
  }

  console.error("No event ID could be determined");
  return null;
}
