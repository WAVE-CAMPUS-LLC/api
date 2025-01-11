document.addEventListener("DOMContentLoaded", function () {
    const applyButtonOne = document.getElementById("applyJobForm");
    const applyButtonTwo = document.getElementById("applyJobFormTwo");
    const applicationCloseBtn = document.getElementById("contentCardClose-button");

    const nextSectionButton = document.getElementById("nextButtonControl");
    const previousSectionButton = document.getElementById("previousButtonControl");
    const sectionOneContainer = document.getElementById("sectionOne");
    const sectionTwoContainer = document.getElementById("sectionTwo");

    const jobApplicationPopup = document.getElementById("jobApplicationForm");


    applyButtonOne.addEventListener("click", () => {
        jobApplicationPopup.style.display = "block";
    });

    applyButtonTwo.addEventListener("click", () => {
        jobApplicationPopup.style.display = "block";
    });

    applicationCloseBtn.addEventListener("click", () => {
        jobApplicationPopup.style.display = "none";
    });

    nextSectionButton.addEventListener("click", () => {
        sectionOneContainer.style.display = "none";
        sectionTwoContainer.style.display = "block";
    });

    previousSectionButton.addEventListener("click", () => {
        sectionOneContainer.style.display = "block";
        sectionTwoContainer.style.display = "none";
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            jobApplicationPopup.style.display = "none";
        }
    });
});
