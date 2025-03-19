document.addEventListener("DOMContentLoaded", function () {
    const fromMobile = document.getElementById("fromMobile")?.value;
    if (fromMobile) {
        setTimeout(() => {
            window.close();
        }, 5000);
    }
});
