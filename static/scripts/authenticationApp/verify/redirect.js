function redirectAfterDelay(url) {
    setTimeout(function() {
        window.location.href = url;
    }, 10000);
}