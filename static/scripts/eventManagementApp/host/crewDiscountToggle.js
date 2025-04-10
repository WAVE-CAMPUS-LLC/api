/**
 * Enhanced Crew Discount Toggle Script
 * Handles the visibility and validation of crew discount fields
 */
document.addEventListener("DOMContentLoaded", function () {
  // Get DOM elements
  const toggleSwitch = document.getElementById("id_crew_discount");
  const crewInfoRow = document.getElementById("crewInfoRow");
  const crewSizeInput = document.getElementById("crew-size-input");
  const crewPercentageInput = document.getElementById("crew-percentage-input");
  const crewSizeError = document.getElementById("crew-size-error");
  const discountError = document.getElementById("discount-error");

  /**
   * Toggle crew info row visibility with smooth transition
   */
  function toggleCrewInfoRow() {
    if (!crewInfoRow) return;
    
    if (toggleSwitch?.checked) {
      // Show with fade-in effect
      crewInfoRow.style.display = "grid";
      setTimeout(() => {
        crewInfoRow.style.opacity = "1";
      }, 10); // Small delay for the transition to work
      
      // Validate fields when enabling
      validateCrewInputs();
    } else {
      // Hide with fade-out effect
      crewInfoRow.style.opacity = "0";
      setTimeout(() => {
        crewInfoRow.style.display = "none";
        
        // Clear validation errors when hiding
        clearValidationErrors();
      }, 300); // Match the CSS transition duration
    }
  }

  /**
   * Clear all validation errors
   */
  function clearValidationErrors() {
    if (crewSizeError) crewSizeError.classList.add("hidden");
    if (discountError) discountError.classList.add("hidden");
    if (crewSizeInput) crewSizeInput.classList.remove("border-red-500");
    if (crewPercentageInput) crewPercentageInput.classList.remove("border-red-500");
  }

  /**
   * Validate crew discount inputs
   * @returns {boolean} Whether all inputs are valid
   */
  function validateCrewInputs() {
    if (!toggleSwitch?.checked) return true;
    
    let isValid = true;
    
    // Validate crew size
    if (crewSizeInput && crewSizeError) {
      const value = crewSizeInput.value.trim();
      const min = parseInt(crewSizeInput.getAttribute("min"), 10) || 2;
      const max = parseInt(crewSizeInput.getAttribute("max"), 10) || 100;
      
      if (!value) {
        isValid = false;
        crewSizeError.textContent = "Minimum crew size is required";
        crewSizeError.classList.remove("hidden");
        crewSizeInput.classList.add("border-red-500");
      } else if (isNaN(value)) {
        isValid = false;
        crewSizeError.textContent = "Please enter a valid number";
        crewSizeError.classList.remove("hidden");
        crewSizeInput.classList.add("border-red-500");
      } else if (parseInt(value, 10) < min) {
        isValid = false;
        crewSizeError.textContent = `Crew size must be at least ${min}`;
        crewSizeError.classList.remove("hidden");
        crewSizeInput.classList.add("border-red-500");
      } else if (parseInt(value, 10) > max) {
        isValid = false;
        crewSizeError.textContent = `Crew size cannot exceed ${max}`;
        crewSizeError.classList.remove("hidden");
        crewSizeInput.classList.add("border-red-500");
      } else {
        crewSizeError.classList.add("hidden");
        crewSizeInput.classList.remove("border-red-500");
      }
    }
    
    // Validate discount percentage
    if (crewPercentageInput && discountError) {
      const value = crewPercentageInput.value.trim();
      const min = parseFloat(crewPercentageInput.getAttribute("min")) || 0.01;
      const max = parseFloat(crewPercentageInput.getAttribute("max")) || 100;
      
      if (!value) {
        isValid = false;
        discountError.textContent = "Discount percentage is required";
        discountError.classList.remove("hidden");
        crewPercentageInput.classList.add("border-red-500");
      } else if (isNaN(value)) {
        isValid = false;
        discountError.textContent = "Please enter a valid number";
        discountError.classList.remove("hidden");
        crewPercentageInput.classList.add("border-red-500");
      } else if (parseFloat(value) < min) {
        isValid = false;
        discountError.textContent = `Discount must be at least ${min}%`;
        discountError.classList.remove("hidden");
        crewPercentageInput.classList.add("border-red-500");
      } else if (parseFloat(value) > max) {
        isValid = false;
        discountError.textContent = `Discount cannot exceed ${max}%`;
        discountError.classList.remove("hidden");
        crewPercentageInput.classList.add("border-red-500");
      } else {
        discountError.classList.add("hidden");
        crewPercentageInput.classList.remove("border-red-500");
      }
    }
    
    return isValid;
  }

  // Attach event listeners
  if (toggleSwitch) {
    toggleSwitch.addEventListener("change", toggleCrewInfoRow);
  }
  
  if (crewSizeInput) {
    crewSizeInput.addEventListener("input", validateCrewInputs);
    crewSizeInput.addEventListener("blur", validateCrewInputs);
  }
  
  if (crewPercentageInput) {
    crewPercentageInput.addEventListener("input", validateCrewInputs);
    crewPercentageInput.addEventListener("blur", validateCrewInputs);
  }

  // Set the initial state on page load
  toggleCrewInfoRow();
  
  // Export validation function for use in form submission
  window.validateCrewDiscountFields = function() {
    // If crew discount is not enabled, return true (valid)
    if (!toggleSwitch?.checked) {
      return true;
    }
    
    return validateCrewInputs();
  };
});
