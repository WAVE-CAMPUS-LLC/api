document.addEventListener('DOMContentLoaded', function () {
    const menuButton = document.getElementById("menuButton");
    const overlay = document.getElementById("overlay");
    const body = document.getElementById('html-content');

    menuButton.addEventListener('click', function () {
        menuButton.classList.toggle("is-active");
        overlay.classList.toggle('show');
        body.classList.toggle('no-scroll');
    })
})