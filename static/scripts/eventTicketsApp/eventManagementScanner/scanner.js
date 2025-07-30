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
        verifyIndividualTicketQRCode(decodedText, qrReader);
      },
      (errorMessage) => {
        console.log(errorMessage);
      }
    )
    .catch((err) => {
      console.error("Camera initialization error:", err);
    });
}

function verifyIndividualTicketQRCode(qrCodeData, qrReader) {
  // Individual ticket QR codes contain JSON data with ticketId and eventId
  const trimmedQRData = qrCodeData.trim();

  console.log(`Verifying individual ticket QR code: ${trimmedQRData}`);

  if (!trimmedQRData) {
    console.error("QR code data is empty.");
    showError("Invalid QR code data.");
    return;
  }

  // Try to parse the QR code data as JSON
  let ticketData;
  try {
    ticketData = JSON.parse(trimmedQRData);
  } catch (e) {
    console.error("QR code data is not valid JSON:", e);
    showError("Invalid QR code format ❌");
    restartScannerAfterDelay(qrReader);
    return;
  }

  // Validate that we have the required fields
  if (!ticketData.ticketId || !ticketData.eventId) {
    console.error("QR code missing required fields:", ticketData);
    showError("Invalid ticket QR code ❌");
    restartScannerAfterDelay(qrReader);
    return;
  }

  console.log(
    `Verifying ticket: ${ticketData.ticketId} for event: ${ticketData.eventId}`
  );

  // Use the individual ticket verification endpoint
  fetch("/api/ticketing/verify_individual_ticket_qr_code/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      qr_code_data: trimmedQRData,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      let name = "Unknown";

      // Extract user or guest name from response
      if (data.user) {
        name =
          `${data.user.first_name || ""} ${data.user.last_name || ""}`.trim() ||
          data.user.username;
      } else if (data.guest) {
        name =
          `${data.guest.first_name || ""} ${
            data.guest.last_name || ""
          }`.trim() || "Guest";
      }

      if (data.valid) {
        showSuccess(`${name}: Valid ✅`);
        console.log(`Successfully verified ticket for: ${name}`);
      } else {
        showError(`${name}: ${data.message || "Invalid"} ❌`);
        console.log(`Ticket verification failed: ${data.message}`);
      }

      // Restart scanner after delay
      restartScannerAfterDelay(qrReader);
    })
    .catch((error) => {
      console.error("Error verifying individual ticket QR code:", error);
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
