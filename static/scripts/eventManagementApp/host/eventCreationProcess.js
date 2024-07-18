document.addEventListener('DOMContentLoaded', function () {
    let currentSectionIndex = 0;

    const sections = document.querySelectorAll('#stage-section');
    const previousButton = document.getElementById('previous-sectionbtn');
    const nextButton = document.getElementById('next-sectionbtn');

    sections.forEach((section, index) => {
        section.style.display = index === 0 ? 'block' : 'none';
    });

    function displaySection(index) {
        sections.forEach((section, i) => {
            section.style.display = i === index ? 'block' : 'none';
        });

        const sectionTitle = sections[index].querySelector('.section-title').value;
        document.title = sectionTitle;

        previousButton.style.display = index === 0 ? 'none' : 'inline-block';
        nextButton.style.display = index === sections.length - 1 ? 'none' : 'inline-block';
    }

    function nextSection() {
        if (currentSectionIndex < sections.length - 1) {
            currentSectionIndex++;
            displaySection(currentSectionIndex);
        }
    }


    function previousSection() {
        if (currentSectionIndex > 0) {
            currentSectionIndex--;
            displaySection(currentSectionIndex);
        }
    }

    nextButton.addEventListener('click', nextSection);
    previousButton.addEventListener('click', previousSection);

    const initialTitle = sections[currentSectionIndex].querySelector('.section-title').value;
    document.title = initialTitle;
    previousButton.style.display = 'none';
    nextButton.style.display = sections.length > 1 ? 'inline-block' : 'none';





    // Overall Ticket Count Processing
    const addTicketButton = document.getElementById("addTicketCount");
    const removeTicketButton = document.getElementById("removeTicketCount");
    const ticketCountInput = document.querySelector(".ticketCountInput");

    let addInterval;
    let removeInterval;

    const incrementTicketCount = () => {
        let currentCount = parseInt(ticketCountInput.value || 0);
        currentCount++;
        ticketCountInput.value = currentCount;
    }

    const decrementTicketCount = () => {
        let currentCount = parseInt(ticketCountInput.value || 0);
        if (currentCount > 0) {
            currentCount--;
            ticketCountInput.value = currentCount;
        }
    }

    // addTicketButton.addEventListener('click', incrementTicketCount);
    // removeTicketButton.addEventListener('click', decrementTicketCount);

    // addTicketButton.addEventListener('mousedown', () => {
    //     addInterval = setInterval(incrementTicketCount, 100); // Adjust the interval time as needed
    // });

    // removeTicketButton.addEventListener('mousedown', () => {
    //     removeInterval = setInterval(decrementTicketCount, 200); // Adjust the interval time as needed
    // });

    // // Add event listeners to clear intervals when mouse button is released
    // addTicketButton.addEventListener('mouseup', () => {
    //     clearInterval(addInterval);
    // });

    // removeTicketButton.addEventListener('mouseup', () => {
    //     clearInterval(removeInterval);
    // });

    // // Add event listeners to clear intervals when mouse leaves the button
    // addTicketButton.addEventListener('mouseleave', () => {
    //     clearInterval(addInterval);
    // });

    // removeTicketButton.addEventListener('mouseleave', () => {
    //     clearInterval(removeInterval);
    // });

    // ticketCountInput.addEventListener('change', () => {
    //     let enteredValue = parseInt(ticketCountInput.value || 0);
    //     if (isNaN(enteredValue) || enteredValue < 0) {
    //         ticketCountInput.value = 0;
    //     }
    // });



    // // Ticket Type Counter System
    // const addTicketTypeButton = document.getElementById("addTicketTypeCount");
    // const removeTicketTypeButton = document.getElementById("removeTicketTypeCount");
    // const ticketTypeCountInput = document.querySelector(".ticketTypeCountInput");

    // let addTypeCountInterval;
    // let removeTypeCountInterval;

    // const incrementTicketTypeCount = () => {
    //     let currentTypeCount = parseInt(ticketTypeCountInput.value || 0);
    //     if (currentTypeCount < 5) {
    //         currentTypeCount++;
    //         ticketTypeCountInput.value = currentTypeCount;
    //     }
    // }

    // const decrementTicketTypeCount = () => {
    //     let currentTypeCount = parseInt(ticketTypeCountInput.value || 0);
    //     if (currentTypeCount > 0) {
    //         currentTypeCount--;
    //         ticketTypeCountInput.value = currentTypeCount;
    //     }
    // }

    // addTicketTypeButton.addEventListener('click', incrementTicketTypeCount);
    // removeTicketTypeButton.addEventListener('click', decrementTicketTypeCount);

    // addTicketTypeButton.addEventListener('mousedown', () => {
    //     addTypeCountInterval = setInterval(incrementTicketTypeCount, 100); // Adjust the interval time as needed
    // });

    // removeTicketTypeButton.addEventListener('mousedown', () => {
    //     removeTypeCountInterval = setInterval(decrementTicketTypeCount, 200); // Adjust the interval time as needed
    // });

    // // Add event listeners to clear intervals when mouse button is released or leaves the button
    // addTicketTypeButton.addEventListener('mouseup', () => {
    //     clearInterval(addTypeCountInterval);
    // });

    // addTicketTypeButton.addEventListener('mouseleave', () => {
    //     clearInterval(addTypeCountInterval);
    // });

    // addTicketTypeButton.addEventListener('mouseout', () => {
    //     clearInterval(addTypeCountInterval);
    // });

    // removeTicketTypeButton.addEventListener('mouseup', () => {
    //     clearInterval(removeTypeCountInterval);
    // });

    // removeTicketTypeButton.addEventListener('mouseleave', () => {
    //     clearInterval(removeTypeCountInterval);
    // });

    // removeTicketTypeButton.addEventListener('mouseout', () => {
    //     clearInterval(removeTypeCountInterval);
    // });

    // ticketTypeCountInput.addEventListener('change', () => {
    //     let enteredTypeValue = parseInt(ticketTypeCountInput.value || 0);
    //     if (isNaN(enteredTypeValue) || enteredTypeValue < 0) {
    //         ticketTypeCountInput.value = 0;
    //     } else if (enteredTypeValue > 5) {
    //         ticketTypeCountInput.value = 5;
    //     }
    // });

})