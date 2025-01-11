$(document).ready(function() {
    // Close all tab bodies except the default one
    $('.jit-tab-body').not('.defaulted').hide(); // Hide all except the default

    // Show the default tab body by sliding down (no need for slideDown since it's already visible)
    $('.jit-role-tab.defaulted .jit-tab-body').slideDown();

    $('.jit-tab-header').click(function() {
        // Close all tab bodies except the one being clicked
        $('.jit-tab-body').not($(this).next('.jit-tab-body')).slideUp();
        // Toggle the visibility of the tab body associated with the clicked header
        $(this).next('.jit-tab-body').slideToggle();
    });
});
