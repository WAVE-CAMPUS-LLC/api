/**
 * Event Carousel - A clean, modern image carousel for the event details page
 * 
 * This script handles the image carousel functionality in the Photos tab
 * of the event details page, providing smooth transitions and thumbnail navigation.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on the event details page with photos
    if (!document.getElementById('image-carousel')) return;

    // Carousel elements
    const carousel = document.getElementById('image-carousel');
    const slides = document.querySelectorAll('.carousel-slide');
    const thumbnails = document.querySelectorAll('.carousel-thumbnail');
    const prevButton = document.getElementById('prev-slide');
    const nextButton = document.getElementById('next-slide');
    
    // If no slides, exit
    if (slides.length === 0) return;
    
    let currentIndex = 0;
    let slideWidth = carousel.clientWidth;
    let autoplayInterval = null;
    
    // Initialize carousel
    function initCarousel() {
        // Set active thumbnail
        updateActiveThumbnail();
        
        // Add event listeners
        prevButton.addEventListener('click', showPreviousSlide);
        nextButton.addEventListener('click', showNextSlide);
        
        // Add thumbnail click events
        thumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                goToSlide(index);
            });
        });
        
        // Handle window resize
        window.addEventListener('resize', handleResize);
        
        // Start autoplay
        startAutoplay();
        
        // Pause autoplay on hover
        carousel.parentElement.addEventListener('mouseenter', stopAutoplay);
        carousel.parentElement.addEventListener('mouseleave', startAutoplay);
    }
    
    // Update the carousel display
    function updateCarousel() {
        slideWidth = carousel.clientWidth;
        carousel.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
        updateActiveThumbnail();
    }
    
    // Handle window resize
    function handleResize() {
        slideWidth = carousel.clientWidth;
        updateCarousel();
    }
    
    // Go to a specific slide
    function goToSlide(index) {
        // Ensure index is within bounds
        if (index < 0) index = slides.length - 1;
        if (index >= slides.length) index = 0;
        
        currentIndex = index;
        updateCarousel();
    }
    
    // Show previous slide
    function showPreviousSlide() {
        goToSlide(currentIndex - 1);
    }
    
    // Show next slide
    function showNextSlide() {
        goToSlide(currentIndex + 1);
    }
    
    // Update active thumbnail
    function updateActiveThumbnail() {
        thumbnails.forEach((thumbnail, index) => {
            if (index === currentIndex) {
                thumbnail.classList.add('border-[#008d95]');
            } else {
                thumbnail.classList.remove('border-[#008d95]');
            }
        });
    }
    
    // Start autoplay
    function startAutoplay() {
        if (autoplayInterval) clearInterval(autoplayInterval);
        autoplayInterval = setInterval(showNextSlide, 5000); // Change slide every 5 seconds
    }
    
    // Stop autoplay
    function stopAutoplay() {
        if (autoplayInterval) {
            clearInterval(autoplayInterval);
            autoplayInterval = null;
        }
    }
    
    // Handle tab switching to ensure correct carousel sizing
    const tabs = document.querySelectorAll('.eventDetailsTab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // If switching to photos tab, update carousel after a short delay
            // to ensure it's visible when we calculate dimensions
            if (this.getAttribute('data-tab') === 'eventPhotosVideos') {
                setTimeout(updateCarousel, 100);
            }
        });
    });
    
    // Initialize the carousel
    initCarousel();
});
