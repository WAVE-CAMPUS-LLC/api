$(document).ready(function() {
    // Close all tab bodies except the default one
    $('.jit-tab-body').not('.defaulted').hide(); // Hide all except the default

    // Show the default tab body by sliding down (no need for slideDown since it's already visible)
    $('.jit-role-tab.defaulted .jit-tab-body').slideDown();

    // Only attach click event to ticket headers that have the role="button" attribute
    // This ensures sold-out tickets (which don't have this attribute) are not clickable
    $('.jit-tab-header[role="button"]').click(function() {
        // Close all tab bodies except the one being clicked
        $('.jit-tab-body').not($(this).next('.jit-tab-body')).slideUp();
        // Toggle the visibility of the tab body associated with the clicked header
        $(this).next('.jit-tab-body').slideToggle();
    });
});
