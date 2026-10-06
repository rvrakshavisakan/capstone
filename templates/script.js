```javascript
// Ethereum Wallet Risk Analysis - Django Frontend Script

function fillWallet(address) {
    const input = document.getElementById('wallet_address');

    if (input) {
        input.value = address;
    }
}

document.addEventListener('DOMContentLoaded', () => {

    const form = document.getElementById('walletForm');

    if (!form) {
        return;
    }

    form.addEventListener('submit', (event) => {

        const input = document.getElementById('wallet_address');
        const errorMsg = document.getElementById('errorMsg');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const btnSpinner = document.getElementById('btnSpinner');

        const wallet = input ? input.value.trim() : '';

        // Validate Ethereum address
        const ethereumAddress = /^0x[a-fA-F0-9]{40}$/;

        if (!ethereumAddress.test(wallet)) {

            event.preventDefault();

            if (errorMsg) {
                errorMsg.textContent =
                    "Please enter a valid Ethereum wallet address.";
                errorMsg.classList.remove('hidden');
            }

            return;
        }

        // Valid address
        if (errorMsg) {
            errorMsg.classList.add('hidden');
        }

        if (submitBtn) {
            submitBtn.disabled = true;
        }

        if (btnText) {
            btnText.textContent = "Starting analysis...";
        }

        if (btnSpinner) {
            btnSpinner.classList.remove('hidden');
        }

        // IMPORTANT:
        // Do NOT call event.preventDefault() here.
        //
        // The form will now be submitted to Django.
        // Django -> home() -> loading page -> analysis -> results
    });
});
```;
