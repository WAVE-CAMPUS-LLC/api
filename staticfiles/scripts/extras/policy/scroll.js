document.addEventListener("DOMContentLoaded", function() {
    // Smooth scrolling function
    function smoothScroll(target, duration) {
        const targetElement = document.querySelector(target);
        const targetPosition = targetElement.offsetTop;
        const startPosition = window.pageYOffset;
        const distance = targetPosition - startPosition;
        const startTime = performance.now();

        function ease(t, b, c, d) {
            // Easing function for smoother scrolling (you can change this)
            t /= d / 2;
            if (t < 1) return c / 2 * t * t + b;
            t--;
            return -c / 2 * (t * (t - 2) - 1) + b;
        }

        function scrollAnimation(currentTime) {
            const timeElapsed = currentTime - startTime;
            const scrollAmount = ease(timeElapsed, startPosition, distance, duration);
            window.scrollTo(0, scrollAmount);
            if (timeElapsed < duration) {
                requestAnimationFrame(scrollAnimation);
            }
        }

        requestAnimationFrame(scrollAnimation);
    }

    // Smooth scroll for anchor links
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = this.getAttribute('href');
            const duration = 1000; // Set duration (in milliseconds) for the scroll animation
            smoothScroll(target, duration);
        });
    });
});
