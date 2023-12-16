document.addEventListener("DOMContentLoaded", function () {
    // Get reference to the left navigation and content container
    const leftNavigation = document.getElementById("left-navigation");
    const contentContainer = document.getElementById("content-container");
    const navItems = leftNavigation.getElementsByTagName("li");

    // Display the profile management content by default
    document.getElementById("profile-body").style.display = "block";

    // Add click event listeners to each navigation item
    leftNavigation.addEventListener("click", function (event) {
        const target = event.target.closest("li");
        if (target) {
            // Get the data-content attribute value to determine the section
            const content = target.getAttribute("data-content");

            // Hide all content sections
            const allContentSections = contentContainer.querySelectorAll(".body > div");
            allContentSections.forEach(section => {
                section.style.display = "none";
            });

            // Display the selected content section based on the clicked item
            switch (content) {
                case "profile":
                    document.getElementById("profile-body").style.display = "block";
                    setActiveButton("profile");
                    break;
                case "billing":
                    document.getElementById("billing-body").style.display = "block";
                    setActiveButton("billing");
                    break;
                case "activity":
                    document.getElementById("activity-body").style.display = "block";
                    setActiveButton("activity");
                    break;
                case "preferences":
                    document.getElementById("preferences-body").style.display = "block";
                    setActiveButton("preferences");
                    break;
                case "security":
                    document.getElementById("security-body").style.display = "block";
                    setActiveButton("security");
                    break;
                case "help":
                    document.getElementById("help-body").style.display = "block";
                    setActiveButton("help");
                    break;
                default:
                    // If no match, display profile by default
                    document.getElementById("profile-body").style.display = "block";
                    setActiveButton("profile");
                    break;
            }
        }
    });

    function setActiveButton(activeContent) {
        // Remove 'active' class from all buttons
        for (let i = 0; i < navItems.length; i++) {
            navItems[i].classList.remove("active");
        }

        // Find the button corresponding to the active content and add 'active' class
        const activeButton = leftNavigation.querySelector(`[data-content="${activeContent}"]`);
        if (activeButton) {
            activeButton.classList.add("active");
        }
    }
});
