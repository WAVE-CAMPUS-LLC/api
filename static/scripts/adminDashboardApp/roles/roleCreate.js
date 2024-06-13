document.addEventListener("DOMContentLoaded", function () {
    const headingCreateButton = document.getElementById("headingCreateRole");
    const createRoleModal = document.getElementById("createRoleModal");
    const closeModalButton = document.getElementById("closeModalButton");

    const roleCards = document.querySelectorAll("[id^=roleHeaderActionBtn]");
    const modals = document.querySelectorAll("[id^=viewGroupModal]");
    const closeButtons = document.querySelectorAll("[id^=closeEditRoleButton]");

    const htmlContent = document.getElementById("html-content");

    roleCards.forEach((card, index) => {
        const modal = modals[index];

        card.addEventListener('click', () => {
            modal.style.display = 'block';
            htmlContent.style.overflow = 'hidden';
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                modal.style.display = 'none';
                htmlContent.style.overflow = 'auto';
            }
        });

        const closeButton = closeButtons[index];
        closeButton.addEventListener('click', () => {
            modal.style.display = 'none';
            htmlContent.style.overflow = 'auto';
        });
    });


    headingCreateButton.addEventListener("click", function () {
        createRoleModal.style.display = "block";
        htmlContent.style.overflow = 'hidden';
    });

    closeModalButton.addEventListener("click", function () {
        createRoleModal.style.display = "none";
        htmlContent.style.overflow = 'auto';
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            createRoleModal.style.display = "none";
            htmlContent.style.overflow = 'auto';
        }
    });




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
    initializeTabSystem('body', 'createRole-tab', 'createRole-tab-content');


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



    const roleNameInput = document.querySelector(".createRoleName");
    const roleCardHeading = document.getElementById('liveRoleNameUpdate');

    const updateHeading = () => {
        const roleName = roleNameInput.value.trim();
        if (roleName) {
            roleCardHeading.textContent = `${roleName}`;
        } else {
            roleCardHeading.textContent = "Role Name";
        }
    };

    roleNameInput.addEventListener("input", updateHeading)
})