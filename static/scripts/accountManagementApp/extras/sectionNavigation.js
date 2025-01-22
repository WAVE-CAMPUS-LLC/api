document.addEventListener("DOMContentLoaded", function() {
    const sections = document.querySelectorAll(".sectionDisplay");
    const nextButton = document.getElementById("nextButton");
    const previousButton = document.getElementById("previousButton");
    const submitButton = document.getElementById("submitButton");
    let currentSectionIndex = 0;

    function showSection(index) {
        sections.forEach((section, i) => {
            section.classList.toggle("hidden", i !== index);
        });
        nextButton.classList.toggle("hidden", index === sections.length - 1);
        submitButton.classList.toggle("hidden", index !== sections.length - 1);
        previousButton.classList.toggle("hidden", index === 0);
    }

    nextButton.addEventListener("click", function() {
        if (currentSectionIndex < sections.length - 1) {
            currentSectionIndex++;
            showSection(currentSectionIndex);
        }
    });

    previousButton.addEventListener("click", function() {
        if (currentSectionIndex > 0) {
            currentSectionIndex--;
            showSection(currentSectionIndex);
        }
    });

    showSection(currentSectionIndex);
});
