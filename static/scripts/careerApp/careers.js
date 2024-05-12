$(document).ready(function() {
    // Close all tab bodies except the default one
    $('.jit-tab-body').not('.defaulted').hide(); // Hide instead of slideUp for initial state
    
    // Show the default tab body by sliding down
    $('.defaulted').slideDown();
    
    $('.jit-tab-header').click(function() {
        // Close all tab bodies except the one being clicked
        $('.jit-tab-body').not($(this).next('.jit-tab-body')).slideUp();
        // Toggle the visibility of the tab body associated with the clicked header
        $(this).next('.jit-tab-body').slideToggle();
    });
});
