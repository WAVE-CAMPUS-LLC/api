document.addEventListener('DOMContentLoaded', function () {
    const rowBody = document.getElementById('row-body');
    const scrollLeftBtn = document.getElementById('scroll-left');
    const scrollRightBtn = document.getElementById('scroll-right');

    const cardWidth = document.querySelector('.category-card').offsetWidth + 20; // card width + gap
    const visibleCards = 4;

    scrollLeftBtn.addEventListener('click', function () {
        rowBody.scrollBy({ left: -(cardWidth * visibleCards), behavior: 'smooth' });
    });

    scrollRightBtn.addEventListener('click', function () {
        rowBody.scrollBy({ left: cardWidth * visibleCards, behavior: 'smooth' });
    });
});
