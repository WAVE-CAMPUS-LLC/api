$(document).ready(function() {
    {% if messages %}
        {% for message in messages %}
            var messageType = "{{ message.tags }}"; // success, error, info, warning
            var messageContent = "{{ message }}";
            
            var notification = $('<div>', {
                class: 'notification ' + messageType,
                text: messageContent,
            });

            // Style the notification depending on type
            notification.css({
                'position': 'absolute',
                'top': '10px',
                'left': '50%',
                'transform': 'translateX(-50%)',
                'padding': '10px',
                'border-radius': '15px',
                'background-color': messageType === 'success' ? '#4CAF50' : messageType === 'error' ? '#f44336' : '#2196F3',
                'color': '#fff',
                'z-index': '9999',
            });

            $('#notification-container').append(notification);

            // Auto-hide the notification after a few seconds
            setTimeout(function() {
                notification.fadeOut('slow', function() {
                    $(this).remove();
                });
            }, 5000);  // Hide after 5 seconds
        {% endfor %}
    {% endif %}
});