$(document).ready(function () {
    const stripe = Stripe(settings.STRIPE_SECRET_KEY);

    const paymentRequest = stripe.paymentRequest({
    country: 'US',
    currency: 'usd',
    total: {
        label: 'Event Tickets',
        amount: totalAmountInCents,
    },
    requestPayerName: true,
    requestPayerEmail: true,
    });

    const elements = stripe.elements();
    const prButton = elements.create('paymentRequestButton', {
    paymentRequest: paymentRequest,
    });

    paymentRequest.canMakePayment().then((result) => {
    if (result) {
        prButton.mount('#payment-request-button');
    } else {
        document.getElementById('payment-request-button').style.display = 'none';
    }
    });

    paymentRequest.on('paymentmethod', async (ev) => {
    const { error } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: ev.paymentMethod.id,
    });
    if (error) {
        ev.complete('fail');
    } else {
        ev.complete('success');
        // Redirect to success page
    }
    });
});
