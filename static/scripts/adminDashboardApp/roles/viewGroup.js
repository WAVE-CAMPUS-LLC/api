document.addEventListener('DOMContentLoaded', function () {
    // Function to handle tab click
    function handleTabClick(tabs, tabContents) {
        tabs.forEach(tab => {
            tab.classList.remove('tab-active');
        });
        this.classList.add('tab-active');

        const tabId = this.getAttribute('data-tab');
        showTabContent(tabContents, tabId);
    }

    // Function to display corresponding content based on tab clicked
    function showTabContent(contents, tabId) {
        contents.forEach(content => {
            content.style.display = 'none';
        });

        const selectedTabContent = document.getElementById(tabId);
        if (selectedTabContent) {
            selectedTabContent.style.display = 'block';
        }
    }

    // Function to initialize tab system for a specific body section
    function initializeTabSystem(modalId) {
        const tabs = document.querySelectorAll(`#${modalId} .viewEditRole-tab`);
        const tabContents = document.querySelectorAll(`#${modalId} .viewEditRole-tab-content`);

        tabs.forEach(tab => {
            tab.addEventListener('click', function () {
                handleTabClick.call(this, tabs, tabContents);
            });
        });

        if (tabs.length > 0 && tabContents.length > 0) {
            tabs[0].classList.add('tab-active');
            showTabContent(tabContents, tabs[0].getAttribute('data-tab'));
        }
    }

    // Select all role cards and their corresponding modals
    const roleCards = document.querySelectorAll('.roleCard');
    const modals = document.querySelectorAll('.viewGroupModal');

    roleCards.forEach((card, index) => {
        const modal = modals[index];

        card.addEventListener('click', () => {
            modal.style.display = 'block';

            // Initialize tab system for the opened modal
            const modalId = modal.id;
            initializeTabSystem(modalId);
        });

        const closeButton = modal.querySelector('.closeModal button');
        closeButton.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    });
});
