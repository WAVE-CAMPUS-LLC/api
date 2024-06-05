document.addEventListener("DOMContentLoaded", function() {
    const headingCreateButton = document.getElementById("headingCreateRole");
    const createRoleModal = document.getElementById("createRoleModal");
    const closeModalButton = document.getElementById("closeModalButton");

    const roleCardInformation = document.querySelectorAll("#roleInformation");
    const closeEditRoleButton = document.querySelectorAll("#closeEditRoleButton");

    roleCardInformation.forEach((card, index) => {
        const editRoleModal = document.getElementById(`viewRoleModal-${index + 1}`);
        card.addEventListener('click', function() {
            editRoleModal.style.display = 'block';
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                editRoleModal.style.display = 'none';
            }
        });
    });

    closeEditRoleButton.forEach((button, index) => {
        button.addEventListener('click', function() {
            const editRoleModal = document.getElementById(`viewRoleModal-${index + 1}`);

            editRoleModal.style.display = 'none';
        })
    })

    headingCreateButton.addEventListener("click", function() {
        createRoleModal.style.display = "block";
    });

    closeModalButton.addEventListener("click", function() {
        createRoleModal.style.display = "none";
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            createRoleModal.style.display = "none";
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
    initializeTabSystem('body', 'editRole-tab', 'editRole-tab-content');
    

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


    
    const colorInput = document.getElementById('roleColorInput');
    const colorCard = document.getElementById('roleInformation');
    const cardBtn = document.getElementById('roleHeaderActionBtn');

    colorInput.addEventListener('input', function() {
        const colorValue = colorInput.value;

        // Validate the hex code
        const hexRegex = /^#([0-9A-F]{3}){1,2}$/i;
        if (hexRegex.test(colorValue)) {
            colorCard.style.backgroundColor = colorValue;
            cardBtn.style.backgroundColor = colorValue;
        } else {
            colorCard.style.backgroundColor = '#008d95'; // Default color if invalid hex
            cardBtn.style.backgroundColor = '#008d95';
        }
    });

})