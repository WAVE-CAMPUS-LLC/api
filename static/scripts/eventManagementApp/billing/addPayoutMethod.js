document.addEventListener('DOMContentLoaded', function () {
    const addPaymentMethodButton = document.getElementById('addPayoutMethodButton');
    const closePayoutMethodButton = document.getElementById('closePayoutMethodButton');
    const payoutMethodModal = document.getElementById('payoutMethodModal');


    addPaymentMethodButton.addEventListener('click', function () {
        payoutMethodModal.classList.remove('hidden');
    });

    closePayoutMethodButton.addEventListener('click', function () {
        payoutMethodModal.classList.add('hidden');
        paymentMethodSelectors.classList.remove('hidden');
        bankAccountForm.classList.add('hidden');
    });

    const paymentMethodSelectors = document.getElementById('paymentMethodSelectors');
    
    const addBankAccountButton = document.getElementById('addBankAccountOption');
    const addCashAppButton = document.getElementById('addCashAppOption');
    const addApplePayButton = document.getElementById('addApplePayOption');
    const addGooglePayButton = document.getElementById('addGooglePayOption');

    const bankAccountForm = document.getElementById('bankAccountForm');

    addBankAccountButton.addEventListener('click', function () {
        paymentMethodSelectors.classList.add('hidden');
        bankAccountForm.classList.remove('hidden');
    });

    addCashAppButton.addEventListener('click', function () {
        paymentMethodSelectors.classList.add('hidden');
    });
});