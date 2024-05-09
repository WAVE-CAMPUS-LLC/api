document.addEventListener('DOMContentLoaded', function () {
    function validateFirstName() {
        var firstNameInput = document.getElementById("id_first_name");
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
    document.getElementById("id_first_name").addEventListener("input", function () {
        validateFirstName();
    });


    function validateLastName() {
        var lastNameInput = document.getElementById("id_last_name");
        var lastNameInputValue = lastNameInput.value.trim();
        var lastNameRegex = /^[A-Za-z]+$/;

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
    document.getElementById("id_last_name").addEventListener("input", function () {
        validateLastName();
    });


    function validateEmail() {
        var emailInput = document.getElementById("id_email");
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
    document.getElementById("id_email").addEventListener("input", function () {
        validateEmail();
    });


    function validateUsername() {
        var usernameInput = document.getElementById("id_username");
        var usernameInputValue = usernameInput.value.trim();
        var usernameRegex = /^[a-zA-Z0-9]+(?:[._][a-zA-Z0-9]+)*$/;


        if (usernameInputValue === "") {
            document.getElementById("usernameLiveValidationError").textContent = "Required";
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
    document.getElementById("id_username").addEventListener("input", function () {
        validateUsername();
    });


    function validatePasswordOne() {
        var passwordInput = document.getElementById("id_password1");
        var passwordInputValue = passwordInput.value;

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
    document.getElementById("id_password1").addEventListener("input", function () {
        validatePasswordOne();
    });


    function validatePasswordTwo() {
        var passwordInput = document.getElementById("id_password1");
        var passwordTwoInput = document.getElementById("id_password2");
        var passwordTwoInputValue = passwordTwoInput.value;

        var passwordOneInputValue = passwordInput.value;

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
    document.getElementById("id_password2").addEventListener("input", function () {
        validatePasswordTwo();
    });


    function validatePhoneNumber(event) {
        var phoneInput = document.getElementById("id_phone_number");
        var phoneInputValue = phoneInput.value.trim();

        var phoneRegex = /^\d{10}$/;

        if (!phoneRegex.test(phoneInputValue)) {
            document.getElementById("phoneLiveValidationError").textContent = "- Invalid format";
            document.getElementById("phoneLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("phoneLiveValidationError").textContent = "";
            document.getElementById("phoneLiveValidationValid").textContent = "- Perfect!";
            return true;
        }
    }
    document.getElementById("id_phone_number").addEventListener("input", function () {
        validatePhoneNumber();
    });


    function validateBirthday() {
        var birthdayMonth = document.getElementById("id_birthday_month").value.trim();
        var birthdayDay = document.getElementById("id_birthday_day").value.trim();
        var birthdayYear = document.getElementById("id_birthday_year").value.trim();

        var birthdayDate = new Date(birthdayYear, birthdayMonth - 1, birthdayDay);

        if (isNaN(birthdayDate) ||
            birthdayDate.getFullYear() != birthdayYear ||
            birthdayDate.getMonth() != birthdayMonth - 1 ||
            birthdayDate.getDate() != birthdayDay ||
            birthdayYear < 1950 ||
            birthdayYear > 2010) {
            document.getElementById("birthdayLiveValidationError").textContent = "Invalid birthday";
            document.getElementById("birthdayLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("birthdayLiveValidationError").textContent = "";
            document.getElementById("birthdayLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }
    document.getElementById("id_birthday_month").addEventListener("input", validateBirthday);
    document.getElementById("id_birthday_day").addEventListener("input", validateBirthday);
    document.getElementById("id_birthday_year").addEventListener("input", validateBirthday);
})