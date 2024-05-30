document.addEventListener("DOMContentLoaded", function() {
    const formSectorOne = document.getElementById("about-yrslf");
    const formSectorTwo = document.getElementById("about-yrorg");
    const formSectorThree = document.getElementById("about-yrevent");

    const sectorOneNextButton = document.getElementById("nextButtonOne");

    const sectorTwoNextButton = document.getElementById("nextButtonTwo");
    const previousButtonSTwo = document.getElementById("previousButtonyrOrg");

    const previousButtonSThree = document.getElementById("previousButtonyrEvent");

    const wwuListItems = document.querySelectorAll("#work-with-us .wwu-heading ul li");
    const wwuListItemSpan = document.querySelectorAll("#work-with-us .wwu-heading ul li span");

    let currentSectionIndex = 0;


    function highlightListItem(index) {
        wwuListItems.forEach((item, i) => {
            if (i === index) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        wwuListItemSpan.forEach((item, i) => {
            if (i === index) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
    }

    sectorOneNextButton.addEventListener('click', function() {
        formSectorOne.style.display = "none";
        formSectorTwo.style.display = 'flex';

        currentSectionIndex++;
        highlightListItem(currentSectionIndex);
    });

    previousButtonSTwo.addEventListener('click', function(){
        formSectorTwo.style.display = "none";
        formSectorOne.style.display = "flex";

        currentSectionIndex--;
        highlightListItem(currentSectionIndex);
    });

    sectorTwoNextButton.addEventListener('click', function(){
        formSectorTwo.style.display = 'none';
        formSectorThree.style.display = 'flex';

        currentSectionIndex++;
        highlightListItem(currentSectionIndex);
    });

    previousButtonSThree.addEventListener('click', function(){
        formSectorThree.style.display = 'none';
        formSectorTwo.style.display = 'flex';

        currentSectionIndex--;
        highlightListItem(currentSectionIndex);
    });

    highlightListItem(currentSectionIndex);
    
});
