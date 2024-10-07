document.addEventListener("DOMContentLoaded", function () {
    const composeEmailAllButton = document.getElementById("emailAllButton");
    const composeEmailModal = document.getElementById("emailModal");
    const composeEmailModalCloseButton = document.getElementById("contentCardClose-button");
    const emailToField = document.getElementById("emailToField");
    const singleEmailButtons = document.querySelectorAll(".singleEmailButton");
    const selectedEmailButton = document.getElementById("emailSelectedButton");
    const memberCheckboxes = document.querySelectorAll(".userCheckbox");
    const sendEmailButton = document.querySelector('.sendEmailButton');

    /**
     * The function `openModalWithEmailPopulated` populates an email input field with a list of emails
     * and displays a compose email modal.
     * @param emails - An array of email addresses.
     */
    function openModalWithEmailPopulated(emails) {
        emailToField.value = emails.join(", ");
        composeEmailModal.style.display = "block";
    }

    /* The `composeEmailAllButton.addEventListener("click", function () { ... })` code block is adding
    a click event listener to the `composeEmailAllButton` element. When the button is clicked, it
    retrieves all the email addresses associated with the member checkboxes on the page by mapping
    over the `memberCheckboxes` array and extracting the `data-email` attribute value from each
    checkbox. These email addresses are then passed to the `openModalWithEmailPopulated` function,
    which populates the email input field in a compose email modal with the list of emails and
    displays the modal. */
    composeEmailAllButton.addEventListener("click", function () {
        const allEmails = Array.from(memberCheckboxes).map((checkbox) =>
            checkbox.getAttribute("data-email")
        );
        openModalWithEmailPopulated(allEmails);
    });

   /* The code block `singleEmailButtons.forEach((button) => {
           button.addEventListener("click", function () {
               const email = button.getAttribute("data-email");
               openModalWithEmailPopulated([email]);
           });
       });` is adding a click event listener to each button in the `singleEmailButtons` NodeList.
   When one of these buttons is clicked, it retrieves the email address associated with that
   specific button by getting the value of the `data-email` attribute of the button. Then, it calls
   the `openModalWithEmailPopulated` function with an array containing the retrieved email address
   as the argument. This action populates the email input field in a compose email modal with the
   clicked email address and displays the modal. */
    singleEmailButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const email = button.getAttribute("data-email");
            openModalWithEmailPopulated([email]);
        });
    });

    /* The code block `memberCheckboxes.forEach((checkbox) => { ... })` is adding a change event
    listener to each checkbox in the `memberCheckboxes` NodeList. When any of these checkboxes are
    changed (checked or unchecked), the function inside the event listener is executed. */
    memberCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", function () {
            const selectedEmails = Array.from(memberCheckboxes)
                .filter((checkbox) => checkbox.checked)
                .map((checkbox) => checkbox.getAttribute("data-email"));

            if (selectedEmails.length > 0) {
                selectedEmailButton.style.display = "inline-block";
            } else {
                selectedEmailButton.style.display = "none";
            }
        });
    });

    /* The `selectedEmailButton.addEventListener("click", function () { ... })` code block is adding a
    click event listener to the `selectedEmailButton` element. When the button associated with
    `selectedEmailButton` is clicked, the function inside the event listener is executed. */
    selectedEmailButton.addEventListener("click", function () {
        const selectedEmails = Array.from(memberCheckboxes)
            .filter((checkbox) => checkbox.checked)
            .map((checkbox) => checkbox.getAttribute("data-email"));
        openModalWithEmailPopulated(selectedEmails);
    });

    /**
     * The function `getCookie` retrieves the value of a specific cookie by its name from the
     * document's cookies.
     * @param name - The `name` parameter in the `getCookie` function is a string representing the name
     * of the cookie you want to retrieve the value for. When you call the `getCookie` function and
     * pass the name of a specific cookie as an argument, the function will search for that cookie in
     * the document
     * @returns The `getCookie` function returns the value of the cookie with the specified name. If
     * the cookie is found, it returns the decoded value of the cookie. If the cookie is not found or
     * the document has no cookies, it returns `null`.
     */
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
    
    /* The code snippet you provided is responsible for sending an email using AJAX (Asynchronous
    JavaScript and XML) when the `sendEmailButton` is clicked. Here's a breakdown of what the code
    is doing: */
    const csrftoken = getCookie('csrftoken');

    // Send email using AJAX
    sendEmailButton.addEventListener("click", function () {
        const recipients = emailToField.value.split(",").map(email => email.trim());
        const message = document.getElementById('emailMessage').value;
        const subject = document.getElementById('emailSubject').value;

        fetch('/theadminportal/send_emailwith_resend/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,  
            },
            body: JSON.stringify({
                recipients: recipients,
                subject: subject,
                message: message,
            }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/theadminportal/emailing/';
                } else {
                    alert('There was an error sending the email.');
                }
            })
            .catch(error => console.error('Error:', error));
    });

    /* The code snippet `composeEmailModalCloseButton.addEventListener("click", function () {
        composeEmailModal.style.display = "none";
    }); */
    composeEmailModalCloseButton.addEventListener("click", function () {
        composeEmailModal.style.display = "none";
    });

    sendEmailButton.addEventListener("click", function (event) {
        event.preventDefault();
    });
});
