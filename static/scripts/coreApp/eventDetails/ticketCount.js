document.addEventListener('DOMContentLoaded', function() {
    function updateTicketCount(ticketId, change) {
        const ticketAmountSpan = document.querySelector(`.currentTicketAmount[data-ticket-id="${ticketId}"]`);
        let currentCount = parseInt(ticketAmountSpan.textContent, 10);

        // Update the ticket count
        currentCount += change;
        if (currentCount < 0) {
            currentCount = 0;
        }
        ticketAmountSpan.textContent = currentCount;
    }

    // Add event listeners to all add/remove buttons
    document.querySelectorAll("#addTicketButton").forEach(button => {
        button.addEventListener("click", function() {
            const ticketId = this.getAttribute("data-ticket-id");
            updateTicketCount(ticketId, 1);  // Increment ticket count for this ticket type
        });
    });

    document.querySelectorAll("#removeTicketButton").forEach(button => {
        button.addEventListener("click", function() {
            const ticketId = this.getAttribute("data-ticket-id");
            updateTicketCount(ticketId, -1);  // Decrement ticket count for this ticket type
        });
    });
});