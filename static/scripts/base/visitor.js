$(document).ready(function () {
    const url = '/track_visitor/';
    $.ajax({
        url: url,         
        type: 'GET',    
        dataType: 'json', 
        success: function (data) {
            console.log("Visitor tracked successfully");
            console.log(data);
            console.log(data.new_visitor);
        },
        error: function (xhr, status, error) {
            console.error("Error occurred while tracking visitor:", error);
        }
    });
});
