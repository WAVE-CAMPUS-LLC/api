document.addEventListener('DOMContentLoaded', function () {
    checkoutButton = document.getElementById('checkoutButton');
    if (checkoutButton) {
        checkoutButton.addEventListener("click", () => {
            checkoutButton.disabled = true;
            checkoutButton.innerHTML = "Processing...";
            checkoutButton.classList.add('opacity-50');
        });
    }

    // Function to handle tab click
    function handleTabClick(tab, tabContents) {
        tab.forEach(tab => {
            tab.classList.remove('eventDeets-tab-active');
        });
        this.classList.add('eventDeets-tab-active');

        // Logic to display corresponding content based on clicked tab
        const tabId = this.getAttribute('data-tab');
        showTabContent(tabContents, tabId);
    }

    // Function to display corresponding content based on tab clicked
    function showTabContent(contents, tabId) {
        // Hide all tab contents
        contents.forEach(content => {
            content.classList.add('hidden');
        });

        // Show the selected tab content
        const selectedTabContent = document.getElementById(tabId);
        if (selectedTabContent) {
            selectedTabContent.classList.remove('hidden');
        }
    }

    // Initialize tab systems for each body section
    initializeTabSystem('contentContainerBodyOne', 'eventDetailsTab', 'eventDetailsTabInformation');

    // Function to initialize tab system for a specific body section
    function initializeTabSystem(bodyId, tabClass, contentClass) {
        const tabs = document.querySelectorAll(`#${bodyId} .${tabClass}`);
        const tabContents = document.querySelectorAll(`#${bodyId} .${contentClass}`);

        tabs.forEach(tab => {
            tab.addEventListener('click', function () {
                handleTabClick.call(this, tabs, tabContents);
            });
        });

        // Show the first tab content and hide all others
        if (tabContents.length > 0) {
            tabContents.forEach((content, index) => {
                if (index === 0) {
                    content.classList.remove('hidden');
                } else {
                    content.classList.add('hidden');
                }
            });
        }

        // Set the first tab as active by default in each body section
        if (tabs.length > 0) {
            tabs[0].classList.add('eventDeets-tab-active');
        }
    }
});

