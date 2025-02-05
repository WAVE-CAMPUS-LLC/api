$(document).ready(function () {
    const url = '/track_visitor/';
    $.ajax({
        url: url,         
        type: 'GET',    
        dataType: 'json', 
        success: function (data) {
            if (data.new_visitor) {
                $('#welcome-popup').removeClass('hidden');
                setTimeout(function () {
                    $('#welcome-popup').fadeOut();
                }, 3000);  
            }
            console.log("Visitor tracked successfully");
            console.log(data);
            console.log(data.new_visitor);
        },
        error: function (xhr, status, error) {
            console.error("Error occurred while tracking visitor:", error);
        }
    });
});
