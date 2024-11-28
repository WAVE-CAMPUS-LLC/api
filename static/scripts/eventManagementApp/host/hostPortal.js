document.addEventListener('DOMContentLoaded', function () {
    function handleTabClick(tab, tabContents) {
        tab.forEach(tab => {
            tab.classList.remove('tab-active');
        });
        this.classList.add('tab-active');

        const tabId = this.getAttribute('data-tab');
        showTabContent(tabContents, tabId);
    }

    function showTabContent(contents, tabId) {
        contents.forEach(content => {
            content.style.display = 'none'; // Hide all contents
        });

        const selectedTabContent = document.getElementById(tabId);
        if (selectedTabContent) {
            selectedTabContent.style.display = 'block'; // Show selected content
        }
    }

    function initializeTabSystem(bodyId, tabClass, contentClass) {
        const tabs = document.querySelectorAll(`#${bodyId} .${tabClass}`);
        const tabContents = document.querySelectorAll(`#${bodyId} .${contentClass}`);

        tabContents.forEach(content => (content.style.display = 'none')); // Hide all initially
        if (tabContents.length > 0) tabContents[0].style.display = 'block'; // Show first by default

        if (tabs.length > 0) {
            tabs[0].classList.add('tab-active');
            const defaultTabId = tabs[0].getAttribute('data-tab');
            showTabContent(tabContents, defaultTabId);
        }

        tabs.forEach(tab => {
            tab.addEventListener('click', function () {
                handleTabClick.call(this, tabs, tabContents);
            });
        });
    }

    initializeTabSystem('portal-body', 'dashboard-tab', 'pbc-element-content');
});
