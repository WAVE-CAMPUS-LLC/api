document.addEventListener('DOMContentLoaded', function () {
    let slideIndex = 0;
    const slides = document.querySelectorAll('#slideshow-container img');
    const totalSlides = slides.length;

    function showSlides() {
        // Hide all slides
        slides.forEach((slide) => {
            slide.classList.remove('image-active');
        });

        // Increment slide index
        slideIndex = (slideIndex + 1) % totalSlides;

        // Show the current slide
        slides[slideIndex].classList.add('image-active');

        // Change slide every 5 seconds (5000 milliseconds)
        setTimeout(showSlides, 5000);
    }

    // Initialize the slideshow
    showSlides();
});
