$(document).ready(function () {
    // Check if it's a new visitor
    const url = document.getElementById('trackVisitorURL').value; // Ensure this input field is set in your HTML
    $.get(url, function (data) {
        if (data.new_visitor) {
            // Show the pop-up if it's a new IP address
            $('#welcome-popup').removeClass('hidden'); // Use `removeClass` to remove the hidden class
            setTimeout(function () {
                $('#welcome-popup').fadeOut();
            }, 3000);  // Pop-up fades out after 3 seconds
        }
    });
});