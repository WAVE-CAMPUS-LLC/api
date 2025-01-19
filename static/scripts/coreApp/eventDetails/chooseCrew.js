document.addEventListener("DOMContentLoaded", function () {
  // Select all the "Choose" buttons for each ticket
  const chooseCrewButtons = document.querySelectorAll(
    "[id^='chooseCrewButton_']"
  );

  chooseCrewButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const buttonId = this.id; // e.g., "chooseCrewButton_1234"
      const ticketId = buttonId.split("_")[1]; // Get ticket ID from button id

      // Show the modal associated with this ticket
      const chooseCrewPopup = document.getElementById(
        "chooseCrewPopup" + ticketId
      );
      chooseCrewPopup.classList.remove("hidden");
    });
  });

  // Close buttons for modals
  const closeButtons = document.querySelectorAll(
    "[id^='closeChooseCrewPopup']"
  );

  closeButtons.forEach((closeBtn) => {
    closeBtn.addEventListener("click", function () {
      const closeBtnId = this.id; // e.g., "closeChooseCrewPopup1234"
      const ticketId = closeBtnId.split("closeChooseCrewPopup")[1]; // Extract ticket ID
      const chooseCrewPopup = document.getElementById(
        "chooseCrewPopup" + ticketId
      );
      chooseCrewPopup.classList.add("hidden");
    });
  });

  // Optional: Toggle ticket description visibility when clicking the "Tap to see more" part
  const ticketTabs = document.querySelectorAll(".jit-tab-header");

  ticketTabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      const tabId = tab.id;
      const ticketId = tabId.split("_")[1]; // Extract ticket ID
      const tabBody = document
        .querySelector(`#chooseCrewButton_${ticketId}`)
        ?.closest(".jit-role-tab")
        .querySelector(".jit-tab-body");

      tabBody?.classList.toggle("hidden");
    });
  });

  // Optional: Handle the add/remove ticket quantity buttons
  const addRemoveButtons = document.querySelectorAll(
    "[id^='addTicketButton'], [id^='removeTicketButton']"
  );

  addRemoveButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const ticketId = this.getAttribute("data-ticket-id");
      const action = this.closest("form")?.querySelector(
        'input[name="eventAction"]'
      ).value;

      if (action === "Add Ticket") {
        const ticketAmount = document.getElementById("currentTicketAmount");
        const newAmount = parseInt(ticketAmount.innerText) + 1;
        ticketAmount.innerText = newAmount;
      } else if (action === "Remove Ticket") {
        const ticketAmount = document.getElementById("currentTicketAmount");
        const newAmount = parseInt(ticketAmount.innerText) - 1;
        ticketAmount.innerText = newAmount;
      }
    });
  });
});
