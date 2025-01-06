document.addEventListener('DOMContentLoaded', function () {
    const shareButton = document.getElementById('shareMyProfile');
    const shareModal = document.getElementById('shareMyProfileModal');
    const closeShareModal = document.getElementById('closeShareMyProfileModal');

    shareButton.addEventListener('click', function () {
        shareModal.classList.remove('hidden');
    });

    closeShareModal.addEventListener('click', function () {
        shareModal.classList.add('hidden');
    });

    const shareLink = document.getElementById('shareLinkCopyButton');
    shareLink.addEventListener('click', function () {
        copyShareLink();
    });

    const copyLinkSuccessUrl = document.getElementById('copyLinkSuccessUrl').value;

    function copyShareLink() {
        const shareLink = document.getElementById('shareLink');
    
        navigator.clipboard.writeText(shareLink.value).then(function () {
            // Send an AJAX request to trigger a Django message
            fetch(copyLinkSuccessUrl, {
                method: 'GET',
            }).then(response => {
                // Check if the response is JSON
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Failed to fetch data');
                }
            })
            .then(data => {
                // Handle successful response
                console.log(data.message); // You can log or use the response data here
                shareModal.classList.add('hidden');
                location.reload();
            })
            .catch(error => {
                console.error('Error with AJAX request:', error);
            });
        }).catch(function (error) {
            console.error('Error copying text to clipboard: ', error);
        });
    }
    

});

