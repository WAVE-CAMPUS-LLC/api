document.addEventListener('DOMContentLoaded', function () {
    // Function to handle tab click
    function handleTabClick(tab, tabContents) {
        tab.forEach(tab => {
            tab.classList.remove('tab-active');
        });
        this.classList.add('tab-active');

        // Logic to display corresponding content based on clicked tab
        const tabId = this.getAttribute('data-tab');
        showTabContent(tabContents, tabId);
    }

    // Function to display corresponding content based on tab clicked
    function showTabContent(contents, tabId) {
        // Hide all tab contents
        contents.forEach(content => {
            content.style.display = 'none';
        });

        // Show the selected tab content
        const selectedTabContent = document.getElementById(tabId);
        if (selectedTabContent) {
            selectedTabContent.style.display = 'block';
        }
    }

    // Initialize tab systems for each body section
    initializeTabSystem('content-container', 'applications-tab', 'applications-tab-content');
    initializeTabSystem('shareModalBody', 'shareTab', 'shareTabInformation');
    initializeTabSystem('sharedEventBody', 'shareEventTab', 'sharedEventsWithTabContainer');
    initializeTabSystem('crewRequestsBody', 'crewRequestTab', 'crewRequestTabContainer');
    initializeTabSystem('myCrewsBody', 'myCrewsTab', 'myCrewsTabContainer');
    initializeTabSystem('sharedFriendRequestsBody', 'friendRequestTab', 'friendRequestTabContainer');


    // Function to initialize tab system for a specific body section
    function initializeTabSystem(bodyId, tabClass, contentClass) {
        const tabs = document.querySelectorAll(`#${bodyId} .${tabClass}`);
        const tabContents = document.querySelectorAll(`#${bodyId} .${contentClass}`);

        tabs.forEach(tab => {
            tab.addEventListener('click', function () {
                handleTabClick.call(this, tabs, tabContents);
            });
        });

        if (tabContents.length > 0) {
            tabContents[0].style.display = 'block';
        }

        // Set the first tab as active by default in each body section
        if (tabs.length > 0) {
            tabs[0].classList.add('tab-active');
            const defaultTabId = tabs[0].getAttribute('data-tab');
            showTabContent(tabContents, defaultTabId);
        }
    }
});