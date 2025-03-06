document.addEventListener("DOMContentLoaded", function () {
  // Get all forms with the college-display-form class
  const forms = document.querySelectorAll(".college-display-form");

  // Add event listeners to each form
  forms.forEach(function (form) {
    const checkbox = form.querySelector(".displayOnCollegeCheckbox");

    if (checkbox) {
      // Style the checkbox
      const checkboxSpan = form.querySelector(".checkbox");

      // Update checkbox appearance based on initial state
      if (checkbox.checked) {
        checkboxSpan.classList.add("bg-[#008d95]", "border-[#008d95]");
      }

      checkbox.addEventListener("change", function () {
        // Toggle the checkbox appearance
        if (checkbox.checked) {
          checkboxSpan.classList.add("bg-[#008d95]", "border-[#008d95]");
        } else {
          checkboxSpan.classList.remove("bg-[#008d95]", "border-[#008d95]");
        }

        // Update the hidden input value
        const hiddenInput = form.querySelector(
          'input[name="displayOnCollegeValue"]'
        );
        if (hiddenInput) {
          hiddenInput.value = checkbox.checked ? "True" : "False";
        }

        // Submit the form when the checkbox state changes
        form.submit();
      });
    }
  });
});
