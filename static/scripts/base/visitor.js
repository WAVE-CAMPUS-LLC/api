$(document).ready(function() {
    // Check if it's a new visitor
    const url = document.getElementById('trackVisitorURL').value;
    $.get(url, function(data) {
        if (data.new_visitor) {
            // Show the pop-up if it's a new IP address

            $('#welcome-popup').classList.remove('hidden');
            setTimeout(function() {
                $('#welcome-popup').fadeOut();
            }, 3000);  // Pop-up fades out after 3 seconds
        }
    });
});