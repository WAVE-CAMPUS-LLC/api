document.addEventListener('DOMContentLoaded', function () {
    // Select all elements with the id 'event-date'
    const eventDateElements = document.querySelectorAll('[id^="event-date-"]');

    eventDateElements.forEach(eventDateElement => {
        const eventDateString = eventDateElement.getAttribute('data-date');
        const eventTimeString = eventDateElement.getAttribute('data-time');

        // Combine date and time into a single string
        const eventDateTimeString = `${eventDateString} ${eventTimeString}`;
        const eventDate = new Date(eventDateTimeString).getTime();

        function updateCountdown() {
            const now = new Date().getTime();
            const timeLeft = eventDate - now;

            if (timeLeft < 0) {
                eventDateElement.textContent = "Event has started!";
                return;
            }

            const days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

            let countdownText = '';

            if (days > 0) {
                countdownText += `${days} ${days === 1 ? 'day' : 'days'}, `;
            }
            if (hours > 0) {
                countdownText += `${hours} ${hours === 1 ? 'hour' : 'hours'}, `;
            }
            if (minutes > 0) {
                countdownText += `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}, `;
            }
            countdownText += `${seconds} ${seconds === 1 ? 'second' : 'seconds'}`;

            eventDateElement.textContent = countdownText;
        }

        // Initial call to update the countdown
        updateCountdown();
        // Update the countdown every second
        setInterval(updateCountdown, 1000);
    });
});
