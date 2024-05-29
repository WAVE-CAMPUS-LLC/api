document.addEventListener('DOMContentLoaded', function () {
    const proceedBtn = document.getElementById("proceedBtn");
    function updateProceedButtonState() {
        const isValid = validatePasswordOne() && validatePasswordTwo();

        proceedBtn.disabled = !isValid;
    }

    const passwordInput = document.getElementById("id_password");
    const confirmPasswordInput = document.getElementById("id_confirm_password");

    function validatePasswordOne() {

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

    function validatePasswordTwo() {
        var passwordTwoInputValue = confirmPasswordInput.value;

        var passwordOneInputValue = passwordInput.value;

        if (passwordTwoInputValue !== passwordOneInputValue) {
            document.getElementById("passwordTwoLiveValidationError").textContent = "No match";
            document.getElementById("passwordTwoLiveValidationValid").textContent = "";
            return false;
        } else {
            document.getElementById("passwordTwoLiveValidationError").textContent = "";
            document.getElementById("passwordTwoLiveValidationValid").textContent = "Perfect!";
            return true;
        }
    }

    passwordInput.addEventListener("input", updateProceedButtonState);
    confirmPasswordInput.addEventListener("input", updateProceedButtonState);

    // Update button state on page load
    updateProceedButtonState();
})