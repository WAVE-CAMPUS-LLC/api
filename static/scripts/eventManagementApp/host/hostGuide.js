document.addEventListener('DOMContentLoaded', function () {
    // Get all the section elements
    const sections = document.querySelectorAll('.guide-section-content');
    
    // Set the first section to be displayed by default
    if (sections.length > 0) {
        sections[0].classList.remove('hidden');  // Show the first section
        sections[0].classList.add('block');      // Ensure it's displayed
    }

    // Set up event listeners for the sidebar links (or buttons) to switch sections
    const sidebarLinks = document.querySelectorAll('.section-link');
    
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();  // Prevent the default anchor behavior

            const targetSectionId = link.getAttribute('href').substring(1);  // Get the section id from href
            const targetSection = document.getElementById(targetSectionId); // Find the corresponding section div

            const targetSectionClass = link.getAttribute('data-target'); // Get the section class from data-target
            const targetSectionContent = document.querySelector(`#${targetSectionClass}`);

            // First, reveal all sections in the target section
            const allTargetSectionDivs = targetSectionContent.querySelectorAll('div');
            allTargetSectionDivs.forEach(div => {
                div.classList.remove('hidden');
                div.classList.add('block');
            });

            // Now, reveal the target section itself
            sections.forEach(section => {
                section.classList.remove('block');
                section.classList.add('hidden');
            });

            targetSectionContent.classList.remove('hidden');
            targetSectionContent.classList.add('block');
            
            // Optionally scroll to the clicked section within the target section
            targetSection.scrollIntoView({ behavior: 'smooth' });
        });
    });
});
