document.addEventListener("DOMContentLoaded", function () {
    const paymentMethodButton = document.getElementById("addPaymentMethodToProfile");
    const paymentMethodModal = document.getElementById("addPaymentMethodModal");
    const closePaymentMethodModal = document.getElementById("closeAddPaymentMethodModal");

    paymentMethodButton.addEventListener("click", function () {
        paymentMethodModal.classList.remove("hidden");
    });

    closePaymentMethodModal.addEventListener("click", function () {
        paymentMethodModal.classList.add("hidden");
    });
});