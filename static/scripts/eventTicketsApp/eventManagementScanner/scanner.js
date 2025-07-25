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

function verifyTicket(qrCodeData, qrReader) {
  // Universal QR codes contain only the UUID string, not JSON
  // Try parsing as JSON first for backward compatibility, then as UUID
  let universalQRCode = qrCodeData.trim();
  let eventId = getEventIdFromPage(); // This function needs to be implemented to get current event ID

  // Check if it's old JSON format (backward compatibility)
  try {
    const ticketObject = JSON.parse(qrCodeData);
    if (ticketObject.ticketId && ticketObject.eventId && ticketObject.status) {
      // Old format - use existing verification
      verifyLegacyTicket(ticketObject, qrReader);
      return;
    }
  } catch (e) {
    // Not JSON, treat as universal QR code UUID
  }

  // New universal QR code format
  if (!universalQRCode || !eventId) {
    console.error("QR code data or event ID is missing.");
    alert("Invalid QR code or event not specified.");
    return;
  }

  // Use the new universal QR verification endpoint
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
      let name = "";

      // Handle universal QR response format
      if (data.user) {
        name =
          `${data.user.first_name || ""} ${data.user.last_name || ""}`.trim() ||
          data.user.username;
      } else if (data.ticketData) {
        // Fallback to legacy format
        if (data.ticketData.guestFirstName && data.ticketData.guestLastName) {
          name = `${data.ticketData.guestFirstName} ${data.ticketData.guestLastName}`;
        } else if (
          data.ticketData.userFirstName &&
          data.ticketData.userLastName
        ) {
          name = `${data.ticketData.userFirstName} ${data.ticketData.userLastName}`;
        }
      }

      if (data.valid) {
        const ticketStatus = document.querySelector(".ticket-status-valid");
        ticketStatus.textContent = `${name}: Valid ✅`;
        ticketStatus.style.display = "block";
      } else {
        const ticketStatus = document.querySelector(".ticket-status-invalid");
        ticketStatus.textContent = `${name || "Unknown"}: ${
          data.message || "Invalid"
        } ❌`;
        ticketStatus.style.display = "block";
      }

      // Hide status after a delay, restart scan for next ticket
      setTimeout(() => {
        document.querySelector(".ticket-status-valid").style.display = "none";
        document.querySelector(".ticket-status-invalid").style.display = "none";

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
    })
    .catch((error) => {
      console.error("Error verifying universal QR code:", error);

      // Show error message
      const ticketStatus = document.querySelector(".ticket-status-invalid");
      ticketStatus.textContent = "Error scanning QR code ❌";
      ticketStatus.style.display = "block";

      // Hide error and restart after delay
      setTimeout(() => {
        ticketStatus.style.display = "none";
        startQrScan(); // Restart the scanner
      }, 3000);
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

// Helper function to get event ID from the current page
function getEventIdFromPage() {
  // Try to get event ID from URL parameters
  const urlParams = new URLSearchParams(window.location.search);
  let eventId = urlParams.get("eventId") || urlParams.get("event_id");

  if (eventId) {
    return eventId;
  }

  // Try to get from page data attributes
  const eventElement = document.querySelector("[data-event-id]");
  if (eventElement) {
    return eventElement.getAttribute("data-event-id");
  }

  // Try to get from form or hidden input
  const hiddenInput = document.querySelector(
    'input[name="eventId"], input[name="event_id"]'
  );
  if (hiddenInput) {
    return hiddenInput.value;
  }

  // Try to get from global JavaScript variable (if set by backend)
  if (typeof eventId !== "undefined" && eventId) {
    return eventId;
  }

  if (typeof window.eventId !== "undefined" && window.eventId) {
    return window.eventId;
  }

  // Fallback: prompt user for event ID
  console.warn("Event ID not found on page. Prompting user.");
  return prompt("Please enter the Event ID for this scanning session:");
}

// Legacy ticket verification for backward compatibility
function verifyLegacyTicket(ticketObject, qrReader) {
  console.log("Using legacy ticket verification for:", ticketObject);

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
          name = `${data.ticketData.guestFirstName} ${data.ticketData.guestLastName}`;
        } else if (
          data.ticketData.userFirstName &&
          data.ticketData.userLastName
        ) {
          name = `${data.ticketData.userFirstName} ${data.ticketData.userLastName}`;
        }
      }

      if (data.valid) {
        const ticketStatus = document.querySelector(".ticket-status-valid");
        ticketStatus.textContent = `${name}: Valid (Legacy) ✅`;
        ticketStatus.style.display = "block";
      } else {
        const ticketStatus = document.querySelector(".ticket-status-invalid");
        ticketStatus.textContent = `${name || "Unknown"}: Invalid (Legacy) ❌`;
        ticketStatus.style.display = "block";
      }

      // Hide status after a delay, restart scan for next ticket
      setTimeout(() => {
        document.querySelector(".ticket-status-valid").style.display = "none";
        document.querySelector(".ticket-status-invalid").style.display = "none";

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
    })
    .catch((error) => {
      console.error("Error verifying legacy ticket:", error);

      // Show error message
      const ticketStatus = document.querySelector(".ticket-status-invalid");
      ticketStatus.textContent = "Error scanning legacy ticket ❌";
      ticketStatus.style.display = "block";

      // Hide error and restart after delay
      setTimeout(() => {
        ticketStatus.style.display = "none";
        startQrScan(); // Restart the scanner
      }, 3000);
    });
}
