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
    initializeTabSystem('support-body', 'supportc-tab', 'content-tabs');

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
            tabContents.forEach(content => {
                content.style.display = 'none';
            });
            tabContents[0].style.display = 'block';
        }

        // Set the first tab as active by default in each body section
        if (tabs.length > 0) {
            tabs[0].classList.add('tab-active');
        }
    }

    // Prevent default form submission for the chat form
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', function (e) {
        e.preventDefault();  // Prevent page reload
        sendMessage();
    });

    // Close chat button functionality
    document.getElementById('closeChat').addEventListener('click', function() {
        const chatContainer = document.getElementById('chatContainer');
        chatContainer.style.display = 'none';
    });

    // Handle Enter key press to send message
    document.getElementById("chat-input").addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();  // Prevent form submission on Enter key press
            sendMessage();
        }
    });
});

// Function to send the chat message
function sendMessage() {
    let userInput = document.getElementById("chat-input").value;
    if (!userInput) return;  // Don't send an empty message

    // Append the user's message to the chat body
    document.getElementById("chat-body").innerHTML += `<p><strong>You:</strong> ${userInput}</p>`;

    // Make the fetch API request to send the message to the server
    fetch("chat/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie('csrftoken')  // Include the CSRF token in the headers
        },
        body: JSON.stringify({
            message: userInput
        })
    })
    .then(response => response.json())
    .then(data => {
        // Append the bot's response to the chat body
        let chatBody = document.getElementById("chat-body");
        if (chatBody) {
            chatBody.innerHTML += `<p><strong>Bot:</strong> ${data.response}</p>`;
            document.getElementById("chat-input").value = "";  // Clear the input field
            chatBody.scrollTop = chatBody.scrollHeight;  // Scroll to the bottom of the chat
        } else {
            console.error('Error: chat-body element not found');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

// Helper function to retrieve the CSRF token from the cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
