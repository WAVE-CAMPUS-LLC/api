document.addEventListener('DOMContentLoaded', function () {
    const proceedBtn = document.getElementById("proceedBtn");

    function updateProceedButtonState() {
        const isValid = validateFirstName() && validateLastName() && validateEmail() && validateUsername() && validatePasswordOne() && validatePasswordTwo();

        proceedBtn.disabled = !isValid;
    }


    const firstNameInput = document.getElementById("id_first_name");
    const lastNameInput = document.getElementById("id_last_name");
    const emailInput = document.getElementById("id_email");
    const usernameInput = document.getElementById("id_username");
    const passwordOneInput = document.getElementById("id_password1");
    const passwordTwoInput = document.getElementById("id_password2");

    const fieldArray = [firstNameInput, lastNameInput, emailInput, usernameInput, passwordOneInput, passwordTwoInput];

    fieldArray.forEach(field => {
        field.value = '';
    });


    function validateFirstName() {
        var firstNameInputValue = firstNameInput.value.trim();
        var firstNameRegex = /^[A-Za-z]+$/;

        if (firstNameInputValue === "") {
            document.getElementById("firstNameLiveValidationError").textContent = "Required";
            document.getElementById("firstNameLiveValidationValid").textContent = "";
            return false;
        } else if (!firstNameRegex.test(firstNameInputValue)) {
            document.getElementById("firstNameLiveValidationError").textContent = "Alphabets only";
            document.getElementById("firstNameLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("firstNameLiveValidationError").textContent = "";
            document.getElementById("firstNameLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    function validateLastName() {
        var lastNameInputValue = lastNameInput.value.trim();
        var lastNameRegex = /^[A-Za-z]+(?:[ '-][A-Za-z]+)*$/;

        if (lastNameInputValue === "") {
            document.getElementById("lastNameLiveValidationError").textContent = "Required";
            document.getElementById("lastNameLiveValidationValid").textContent = "";
            return false;
        } else if (!lastNameRegex.test(lastNameInputValue)) {
            document.getElementById("lastNameLiveValidationError").textContent = "Alphabets only";
            document.getElementById("lastNameLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("lastNameLiveValidationError").textContent = "";
            document.getElementById("lastNameLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    function validateEmail() {
        var emailInputValue = emailInput.value.trim();
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (emailInputValue === "") {
            document.getElementById("emailLiveValidationError").textContent = "- Required";
            document.getElementById("emailLiveValidationValid").textContent = "";
            return false;
        } else if (!emailRegex.test(emailInputValue)) {
            document.getElementById("emailLiveValidationError").textContent = "- Invalid email";
            document.getElementById("emailLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("emailLiveValidationError").textContent = "";
            document.getElementById("emailLiveValidationValid").textContent = "- Perfect!";
            return true;
        }
    }


    function validateUsername() {
        var usernameInputValue = usernameInput.value.trim();
        var usernameRegex = /^[a-zA-Z0-9]+(?:[._][a-zA-Z0-9]+)*$/;


        if (usernameInputValue === "") {
            document.getElementById("usernameLiveValidationError").textContent = "Required";
            document.getElementById("usernameLiveValidationValid").textContent = "";
            return false;
        }
        else if (usernameInputValue.length < 6) {
            document.getElementById("usernameLiveValidationError").textContent = "Minimum of 6 characters required";
            document.getElementById("usernameLiveValidationValid").textContent = "";
            return false;
        }
        else if (usernameInputValue.length > 20) {
            document.getElementById("usernameLiveValidationError").textContent = "Too long";
            document.getElementById("usernameLiveValidationValid").textContent = "";
        }
        else if (!usernameRegex.test(usernameInputValue)) {
            for (var i = 0; i < usernameInputValue.length; i++) {
                var char = usernameInputValue.charAt(i);
                // Check if the character is invalid
                if (!usernameRegex.test(char)) {
                    // Show error message with the invalid character
                    document.getElementById("usernameLiveValidationError").textContent = "Invalid character: '" + char + "'";
                    document.getElementById("usernameLiveValidationValid").textContent = "";
                    return false;
                }
            }
        }
        else {
            document.getElementById("usernameLiveValidationError").textContent = "";
            document.getElementById("usernameLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    function validatePasswordOne() {

        var passwordInputValue = passwordOneInput.value;

        if (passwordInputValue === "") {
            document.getElementById("passwordOneLiveValidationError").textContent = "Required";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (passwordInputValue.length < 8) {
            // Checking password length
            document.getElementById("passwordOneLiveValidationError").textContent = "Too short";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (!/[A-Z]/.test(passwordInputValue)) {
            document.getElementById("passwordOneLiveValidationError").textContent = "Uppercase required";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (!/[a-z]/.test(passwordInputValue)) {
            document.getElementById("passwordOneLiveValidationError").textContent = "Lowercase required";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (!/\d/.test(passwordInputValue)) {
            document.getElementById("passwordOneLiveValidationError").textContent = "Digit required";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (!/[!@#$%^&*()_+[\]{};':"\\|,.<>/?]/.test(passwordInputValue)) {
            document.getElementById("passwordOneLiveValidationError").textContent = "Character required";
            document.getElementById("passwordOneLiveValidationValid").textContent = "";
            return false;
        }

        if (/[!@#$%^&*()_+[\]{};':"\\|,.<>/?]/.test(passwordInputValue) && /\d/.test(passwordInputValue) && /[a-z]/.test(passwordInputValue) && /[A-Z]/.test(passwordInputValue) && !(passwordInputValue.length < 8)) {
            // Present "Perfect" if validation passes!
            document.getElementById("passwordOneLiveValidationError").textContent = "";
            document.getElementById("passwordOneLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    function validatePasswordTwo() {
        var passwordTwoInputValue = passwordTwoInput.value;

        var passwordOneInputValue = passwordOneInput.value;

        if (passwordTwoInputValue !== passwordOneInputValue) {
            document.getElementById("passwordTwoLiveValidationError").textContent = "Passwords must match";
            document.getElementById("passwordTwoLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("passwordTwoLiveValidationError").textContent = "";
            document.getElementById("passwordTwoLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    firstNameInput.addEventListener("input", updateProceedButtonState);
    lastNameInput.addEventListener("input", updateProceedButtonState);
    emailInput.addEventListener("input", updateProceedButtonState);
    usernameInput.addEventListener("input", updateProceedButtonState);
    passwordOneInput.addEventListener("input", updateProceedButtonState);
    passwordTwoInput.addEventListener("input", updateProceedButtonState);

    // Update button state on page load
    updateProceedButtonState();
})