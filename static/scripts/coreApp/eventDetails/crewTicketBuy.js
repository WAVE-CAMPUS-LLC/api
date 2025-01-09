document.addEventListener("DOMContentLoaded", function () {
  const crewPurchaseButtons = document.querySelectorAll(".crewPurchaseButton");
  const crewPurchaseDisplay = document.getElementById("crewPurchaseDisplay");
  const crewPurchaseCloseButton = document.getElementById(
    "crewPurchaseCloseButton"
  );
  let currentTicketId = null;

  // Show crew purchase modal when the "Purchase for your crew" button is clicked
  document.querySelectorAll("#crewPurchaseButton").forEach((button) => {
    button.addEventListener("click", function () {
      currentTicketId = this.getAttribute("data-ticket-id");
      if (!currentTicketId) {
        console.error("No ticket ID found");
        alert("Error: Could not determine ticket ID");
        return;
      }
      crewPurchaseDisplay.classList.remove("hidden");
    });
  });

  // Close crew purchase modal
  if (crewPurchaseCloseButton) {
    crewPurchaseCloseButton.addEventListener("click", function () {
      crewPurchaseDisplay.classList.add("hidden");
    });
  }

  // Handle crew purchase form submission
  crewPurchaseButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const form = this.closest("form");
      if (!form) {
        console.error("Form not found");
        alert("Error: Could not find the purchase form");
        return;
      }

      const crewId = form.querySelector('input[name="crewId"]').value;
      const csrfToken = form.querySelector(
        'input[name="csrfmiddlewaretoken"]'
      ).value;
      const crewPurchaseUrl = form.querySelector(
        'input[name="crewPurchaseUrl"]'
      ).value;

      if (!crewPurchaseUrl) {
        console.error("Crew purchase URL not found");
        alert("Error: Could not find the purchase URL");
        return;
      }

      if (!crewId || !currentTicketId) {
        console.error("Missing required data", { crewId, currentTicketId });
        alert("Error: Missing required information for purchase");
        return;
      }

      // Show loading state
      button.disabled = true;
      button.textContent = "Processing...";

      fetch(crewPurchaseUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          crewId: crewId,
          ticketId: currentTicketId,
        }),
        credentials: "same-origin",
      })
        .then((response) => {
          if (!response.ok) {
            return response.json().then((data) => {
              throw new Error(data.error || "Server error occurred");
            });
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            window.location.href = data.redirectUrl;
          } else {
            throw new Error(data.error || "Unknown error occurred");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert(
            "Error: " +
              (error.message ||
                "An error occurred while processing your request.")
          );
        })
        .finally(() => {
          // Reset button state
          button.disabled = false;
          button.textContent = "Purchase";
        });
    });
  });
});
