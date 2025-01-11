document.addEventListener('DOMContentLoaded', function () {
    const addBankAccountButton = document.getElementById('addBankAccountButton');
    const addCardButton = document.getElementById('addCardButton');
    const closeCardPaymentButton = document.getElementById('closeCardPaymentButton');
    const closeBankAccountButton = document.getElementById('closeBankAccountButton');
    const addBankAccountModal = document.getElementById('addBankAccountModal');
    const addCardModal = document.getElementById('addCardModal');

    if (addBankAccountButton) {
        addBankAccountButton.addEventListener('click', function () {
            if (addBankAccountModal) {
                addBankAccountModal.classList.remove('hidden');
            }
        });
    }

    if (addCardButton) {
        addCardButton.addEventListener('click', function () {
            if (addCardModal) {
                addCardModal.classList.remove('hidden');
            }
        });
    }

    if (closeBankAccountButton) {
        closeBankAccountButton.addEventListener('click', function () {
            if (addBankAccountModal) {
                addBankAccountModal.classList.add('hidden');
            }
        });
    }

    if (closeCardPaymentButton) {
        closeCardPaymentButton.addEventListener('click', function () {
            if (addCardModal) {
                addCardModal.classList.add('hidden');
            }
        });
    }
});