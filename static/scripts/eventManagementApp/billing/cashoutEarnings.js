document.addEventListener('DOMContentLoaded', function () {
    const cashoutButton = document.getElementById('cashoutButton');
    const cashoutModal = document.getElementById('cashoutEarningsModal');
    const cashoutModalCloseButton = document.getElementById('closeCashoutEarningsButton');

    cashoutButton.addEventListener('click', function () {
        cashoutModal.classList.remove('hidden');
    });

    cashoutModalCloseButton.addEventListener('click', function () {
        cashoutModal.classList.add('hidden');
    });

    cashoutModal.addEventListener('click', function (event) {
        if (event.target === cashoutModal) {
            cashoutModal.classList.add('hidden');
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            cashoutModal.classList.add('hidden');
        }
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Check if this cookie string begins with the name we want
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(
                        cookie.substring(name.length + 1)
                    );
                    break;
                }
            }
        }
        return cookieValue;
    }


    const processCashoutButton = document.getElementById('processCashoutButton');
    processCashoutButton.addEventListener('click', function (event) {
        event.preventDefault();

        const cashoutAmountInput = document.getElementById('cashoutInputAmount');
        const availableBalance = parseFloat(document.getElementById('cashoutAvailableAmount').value);

        const cashoutAmountValue = parseFloat(cashoutAmountInput.value);
        if (isNaN(cashoutAmountValue) || cashoutAmountValue <= 0 || cashoutAmountValue > parseFloat(availableBalance)) {
            alert("Invalid cashout amount.");
            return;
        }

        const cashoutUrl = document.getElementById('billingCashoutUrl').value;
        fetch(cashoutUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ amount: cashoutAmountValue.toFixed(2) }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Cashout successful');
                    cashoutModal.classList.add('hidden');
                } else {
                    alert('Cashout failed');
                }
            }).catch(error => {
                console.error('Error cashing out:', error);
                alert('An error occurred while cashing out');
            });
    });


});