document.addEventListener('DOMContentLoaded', () => {
    // Cache selectors for performance
    const $form = $("#eventForm");
    const $submitBtn = $("#submitBtn");
    const $cannotSubmit = $("#cannotSubmit");
    const $crewDiscountCheckbox = $("#id_crew_discount"); // Assumes auto_id "id_crew_discount"
    const $crewDiscountDetails = $("#crewInfoRow");
    const $showGuestListCheckbox = $("#id_show_guest_list");
    const touchedFields = {};
    
    // Get the existing form feedback element
    const $formFeedback = $("#form-feedback");
  
    // Validation rules configuration
    const validationRules = {
      ".title-input": {
        required: true,
        minLength: 3,
        maxLength: 100,
        errorSelector: "#title-error",
        messages: {
          required: "Please enter a title",
          minLength: "Title must be at least 3 characters",
          maxLength: "Title must be 100 characters or less"
        }
      },
      ".event-type-input": {
        required: true,
        errorSelector: "#event-type-error",
        messages: {
          required: "Please choose an option"
        }
      },
      ".date-input": {
        required: true,
        validate: function (value) {
          const selectedDate = new Date(value);
          const currentDate = new Date();
          const futureLimitDate = new Date(currentDate);
          
          // Allow events to be created for today
          currentDate.setHours(0, 0, 0, 0);
          
          // Set future limit to 1 year
          futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
          
          if (isNaN(selectedDate.getTime())) return "Please enter a valid date";
          if (selectedDate < currentDate) return "Date cannot be in the past";
          if (selectedDate > futureLimitDate) return "Date cannot be more than a year into the future";
          return "";
        },
        errorSelector: "#date-error",
        messages: {
          required: "Please enter a date"
        }
      },
      ".start-time-input": {
        required: true,
        errorSelector: "#time-error",
        messages: {
          required: "Please enter start time"
        }
      },
      ".end-time-input": {
        required: true,
        errorSelector: "#time-error",
        messages: {
          required: "Please enter end time"
        }
      },
      ".event-visibility-input": {
        required: true,
        errorSelector: "#visibility-error",
        messages: {
          required: "Please choose an option"
        }
      },
      ".building-input": {
        required: false,
        maxLength: 100,
        errorSelector: "#building-error",
        messages: {
          maxLength: "Building name needs to be shorter"
        }
      },
      ".street-input": {
        required: true,
        maxLength: 100,
        errorSelector: "#street-error",
        messages: {
          required: "Please enter a street",
          maxLength: "Street needs to be shorter"
        }
      },
      ".apt-input": {
        required: false,
        maxLength: 50,
        errorSelector: "#apt-error",
        messages: {
          maxLength: "Apt needs to be shorter"
        }
      },
      ".city-input": {
        required: true,
        errorSelector: "#city-error",
        messages: {
          required: "Please enter a city/town"
        }
      },
      ".state-input": {
        required: true,
        errorSelector: "#state-error",
        messages: {
          required: "Please choose an option"
        }
      },
      ".zip-input": {
        required: true,
        minLength: 5,
        errorSelector: "#zip-error",
        messages: {
          required: "Please enter a ZIP code",
          minLength: "ZIP code needs to be longer"
        }
      }
    };
  
    // Helper functions
    function showError(selector, message) {
      $(selector).text(message).removeClass("hidden");
    }
  
    function hideError(selector) {
      $(selector).addClass("hidden").text("");
    }
  
    function setBorder($el, isError) {
      $el.css("border-color", isError ? "#ff0707" : "");
    }
    
    function showFeedback(message, isSuccess = true) {
      // Create appropriate icon based on status
      const icon = isSuccess 
        ? '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>'
        : '<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
      
      // Show the feedback element and set its content
      $formFeedback
        .removeClass('hidden')
        .removeClass('bg-green-100 bg-red-100')
        .addClass(isSuccess ? 'bg-green-100' : 'bg-red-100')
        .html(`<div class="flex items-center justify-between">
                <div class="flex items-center">
                  <span class="${isSuccess ? 'text-green-600' : 'text-red-600'}">${icon}</span>
                  <span class="${isSuccess ? 'text-green-700' : 'text-red-700'} font-Wanted-Medium">${message}</span>
                </div>
                <button class="${isSuccess ? 'text-green-600' : 'text-red-600'} hover:opacity-75" onclick="document.getElementById('form-feedback').classList.add('hidden');">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </button>
              </div>`);
      
      // Scroll to feedback if it's an error
      if (!isSuccess) {
        $('html, body').animate({
          scrollTop: $formFeedback.offset().top - 100
        }, 500);
      }
      
      // Add a subtle animation effect for errors
      if (!isSuccess) {
        // Add shake animation class if it doesn't exist yet
        if (!document.getElementById('shake-animation')) {
          const styleElement = document.createElement('style');
          styleElement.id = 'shake-animation';
          styleElement.textContent = `
            @keyframes shake {
              0%, 100% { transform: translateX(0); }
              10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
              20%, 40%, 60%, 80% { transform: translateX(5px); }
            }
            .shake { animation: shake 0.5s; }
          `;
          document.head.appendChild(styleElement);
        }
        
        $formFeedback.addClass('shake');
        setTimeout(() => {
          $formFeedback.removeClass('shake');
        }, 500);
      }
      
      // Auto-hide after delay
      setTimeout(() => {
        $formFeedback.fadeOut('slow', function() {
          $(this).addClass('hidden').css('display', '');
        });
      }, 5000);
    }
  
    function validateField($field, rules) {
      const value = $field.val().trim();
      let isValid = true;
      let errorMsg = "";
      
      // Required field validation
      if (rules.required && !value) {
        isValid = false;
        errorMsg = rules.messages.required;
      }
      
      // Min length validation
      if (isValid && rules.minLength && value.length < rules.minLength) {
        isValid = false;
        errorMsg = rules.messages.minLength;
      }
      
      // Max length validation
      if (isValid && rules.maxLength && value.length > rules.maxLength) {
        isValid = false;
        errorMsg = rules.messages.maxLength;
      }
      
      // Custom validation function
      if (isValid && typeof rules.validate === "function") {
        const customError = rules.validate(value);
        if (customError) {
          isValid = false;
          errorMsg = customError;
        }
      }
      
      // Show error only if the field has been touched
      if (touchedFields[$field.attr("id")]) {
        if (!isValid) {
          showError(rules.errorSelector, errorMsg);
          setBorder($field, true);
          $field.attr('aria-invalid', 'true');
          $field.attr('aria-describedby', rules.errorSelector.substring(1));
        } else {
          hideError(rules.errorSelector);
          setBorder($field, false);
          $field.attr('aria-invalid', 'false');
          $field.removeAttr('aria-describedby');
        }
      }
      
      return isValid;
    }
  
    function validateTimeFields() {
      const startTime = $(".start-time-input").val();
      const endTime = $(".end-time-input").val();
      const date = $(".date-input").val();
      let valid = true;
      
      // Check if both times are provided
      if (!startTime || !endTime) {
        showError("#time-error", "Both start and end times are required");
        $(".start-time-input, .end-time-input").css("border-color", "#ff0707");
        valid = false;
        return valid;
      }
      
      // Check if end time is after start time
      if (startTime && endTime && date) {
        const startDateTime = new Date(`${date}T${startTime}`);
        const endDateTime = new Date(`${date}T${endTime}`);
        
        if (!isNaN(startDateTime.getTime()) && !isNaN(endDateTime.getTime())) {
          if (endDateTime <= startDateTime) {
            showError("#time-error", "End time must be after start time");
            $(".end-time-input").css("border-color", "#ff0707");
            valid = false;
            return valid;
          }
        }
      }
      
      // If all validations pass
      hideError("#time-error");
      $(".start-time-input, .end-time-input").css("border-color", "");
      return valid;
    }
  
    function validateQuill() {
      if (typeof quill !== "undefined" && quill instanceof Quill) {
        const text = quill.getText().trim();
        const content = quill.root.innerHTML;
        
        // Update the hidden textarea with the HTML content
        $(".description-textarea").val(content);
        
        // Validate the content
        if (text.length === 0) {
          showError("#body-error", "Please enter a description");
          $(".ql-container").css("border-color", "#ff0707");
          return false;
        } else if (text.length < 20) {
          showError("#body-error", "Description should be at least 20 characters");
          $(".ql-container").css("border-color", "#ff0707");
          return false;
        } else if (text.length > 5000) {
          showError("#body-error", "Description must be 5000 characters or less");
          $(".ql-container").css("border-color", "#ff0707");
          return false;
        } else {
          hideError("#body-error");
          $(".ql-container").css("border-color", "");
          return true;
        }
      }
      return true;
    }
  
    function validateCrewDiscount() {
      if ($crewDiscountCheckbox.is(":checked")) {
        const minCrew = parseInt($("#crew-size-input").val(), 10);
        const discount = parseFloat($("#crew-percentage-input").val());
        let valid = true;
        
        // Validate minimum crew size
        if (isNaN(minCrew) || minCrew < 2 || minCrew > 100) {
          showError("#crew-size-error", "Crew size must be between 2 and 100");
          $("#crew-size-input").css("border-color", "#ff0707");
          valid = false;
        } else {
          hideError("#crew-size-error");
          $("#crew-size-input").css("border-color", "");
        }
        
        // Validate discount percentage
        if (isNaN(discount) || discount <= 0 || discount > 100) {
          showError("#discount-error", "Discount must be between 0.01 and 100%");
          $("#crew-percentage-input").css("border-color", "#ff0707");
          valid = false;
        } else {
          hideError("#discount-error");
          $("#crew-percentage-input").css("border-color", "");
        }
        
        return valid;
      } else {
        // If crew discount is not checked, clear any errors
        hideError("#crew-size-error");
        hideError("#discount-error");
        $("#crew-size-input, #crew-percentage-input").css("border-color", "");
        
        // Clear the input values when unchecked
        $("#crew-size-input, #crew-percentage-input").val('');
        
        return true;
      }
    }
  
    function validateHeaderPhoto() {
      const photoInput = $("#photo-input")[0];
      const hasPhoto = photoInput?.files.length > 0;
      const hasExistingPhoto = $("#header-photo-preview").is(":visible") && 
                              $("#header-photo-preview").attr("src") && 
                              $("#header-photo-preview").attr("src") !== "#" &&
                              !$("#header-photo-preview").attr("src").includes("display.png");
      
      if (!hasPhoto && !hasExistingPhoto) {
        showError("#photo-error", "Please upload a header photo");
        $(".h-full.w-full.py-12.px-12.border.border-dashed").css("border-color", "#ff0707");
        return false;
      } else {
        // If there's a new photo, validate its size and type
        if (hasPhoto) {
          const file = photoInput.files[0];
          const maxSize = 5 * 1024 * 1024; // 5MB
          const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
          
          if (file.size > maxSize) {
            showError("#photo-error", "Image must be less than 5MB");
            $(".h-full.w-full.py-12.px-12.border.border-dashed").css("border-color", "#ff0707");
            return false;
          }
          
          if (!allowedTypes.includes(file.type)) {
            showError("#photo-error", "Please upload a JPG, PNG, GIF, or WebP image");
            $(".h-full.w-full.py-12.px-12.border.border-dashed").css("border-color", "#ff0707");
            return false;
          }
        }
        
        hideError("#photo-error");
        $(".h-full.w-full.py-12.px-12.border.border-dashed").css("border-color", "");
        return true;
      }
    }
  
    function validateAll() {
      let overallValid = true;
      
      // Validate each field defined in validationRules
      $.each(validationRules, function (selector, rules) {
        $(selector).each(function () {
          if (!validateField($(this), rules)) {
            overallValid = false;
          }
        });
      });
      
      // Validate time fields
      if (!validateTimeFields()) {
        overallValid = false;
      }
      
      // Validate Quill editor content
      if (!validateQuill()) {
        overallValid = false;
      }
      
      // Use the enhanced crew discount validation from crewDiscountToggle.js if available
      if (typeof window.validateCrewDiscountFields === 'function') {
        if (!window.validateCrewDiscountFields()) {
          overallValid = false;
        }
      } else {
        // Fallback to the old validation method
        if ($(".ticketing-input").val() === "Paid") {
          if (!validateCrewDiscount()) {
            overallValid = false;
          }
        }
      }
      
      // Validate header photo
      if (!validateHeaderPhoto()) {
        overallValid = false;
      }
      
      // Update UI based on validation result
      toggleSubmitButtons(overallValid);
      
      return overallValid;
    }
  
    function toggleSubmitButtons(isValid) {
      if (isValid) {
        $submitBtn.show();
        $cannotSubmit.hide();
      } else {
        $submitBtn.hide();
        $cannotSubmit.show();
      }
      
      // Update the disabled button text to be more helpful
      if (!isValid) {
        $("#cannotSubmit button").text("Please fix form errors");
      }
    }
  
    // Debounce function to limit rapid calls
    function debounce(fn, delay) {
      var timer = null;
      return function () {
        var context = this,
            args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () {
          fn.apply(context, args);
        }, delay);
      };
    }
  
    // Helper: get matching rule selector for a field
    function getMatchingRuleSelector($field) {
      for (var selector in validationRules) {
        if ($field.is(selector)) return selector;
      }
      return null;
    }
  
    // Bind events to inputs, textareas, and selects within the form
    $form.find("input, textarea, select")
      .on("input change", debounce(function () {
        var $field = $(this);
        touchedFields[$field.attr("id")] = true;
        var ruleSelector = getMatchingRuleSelector($field);
        if (ruleSelector) {
          validateField($field, validationRules[ruleSelector]);
        }
        // Cross-field validations
        if ($field.hasClass("start-time-input") || $field.hasClass("end-time-input")) {
          validateTimeFields();
        }
        if ($field.is("#crew-size-input, #crew-percentage-input") || $field.is("#id_crew_discount")) {
          validateCrewDiscount();
        }
        validateAll();
      }, 300))
      .on("blur", function () {
        touchedFields[$(this).attr("id")] = true;
        validateAll();
      });
  
    $("#photo-input").on("change", function () {
      validateHeaderPhoto();
      validateAll();
    });
  
    if (typeof quill !== "undefined" && quill instanceof Quill) {
      quill.on("text-change", function () {
        touchedFields["quill-editor"] = true;
        validateQuill();
        validateAll();
      });
    }
  
    // Toggle crew discount details when the checkbox changes
    $crewDiscountCheckbox.on("change", function () {
      $crewDiscountDetails.toggle($crewDiscountCheckbox.is(":checked"));
      validateCrewDiscount();
      validateAll();
    });
  
    // Initial setup on page load
    $crewDiscountDetails.toggle($crewDiscountCheckbox.is(":checked"));
    validateAll();
  
    // Form submit handler
    $form.on("submit", function (e) {
      e.preventDefault();
      
      // Mark all fields as touched for complete validation
      $form.find("input, textarea, select").each(function() {
        touchedFields[$(this).attr("id")] = true;
      });
      touchedFields["quill-editor"] = true;
      
      if (!validateAll()) {
        showFeedback("Please correct the highlighted errors in the form before submitting.", false);
        
        // Scroll to the first error with improved selector that matches our new UI
        const $firstError = $(".text-\\[\\#FF0707\\]:not(.hidden), .text-\\[\\#FF0000\\]:not(.hidden), .border-red-500").first();
        if ($firstError.length) {
          $('html, body').animate({
            scrollTop: $firstError.offset().top - 100
          }, 500);
        }
        
        // Ensure crew discount section is visible if there are errors
        if ($crewDiscountCheckbox.is(":checked")) {
          const $crewErrors = $("#crew-size-error:not(.hidden), #discount-error:not(.hidden)");
          if ($crewErrors.length) {
            $crewDiscountDetails.show();
            $crewDiscountDetails.css("opacity", "1");
          }
        }
        
        return false;
      }
      
      // Show loading state with improved UI
      const $submitButton = $("#submitBtn button");
      const originalText = $submitButton.text();
      $submitButton.html('<span class="inline-block animate-spin mr-2">↻</span> Saving...');
      $submitButton.prop('disabled', true);
      
      // Submit the form via AJAX
      const formData = new FormData(this);
      
      $.ajax({
        url: $(this).attr('action'),
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
          showFeedback("Event updated successfully!", true);
          
          // Update last saved time if element exists
          const now = new Date();
          const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
          const $lastSaved = $("#last-saved");
          if ($lastSaved.length) {
            $lastSaved.text(`Last saved: ${timeString}`).removeClass("hidden");
          }
          
          // Reset form change tracker if one exists
          if (typeof window.formHasChanges !== 'undefined') {
            window.formHasChanges = false;
          }
        },
        error: function(xhr) {
          let errorMsg = "There was an error updating the event.";
          if (xhr.responseJSON && xhr.responseJSON.error) {
            errorMsg = xhr.responseJSON.error;
          }
          showFeedback(errorMsg, false);
        },
        complete: function() {
          // Restore button state
          $submitButton.html(originalText);
          $submitButton.prop('disabled', false);
        }
      });
      
      return false;
    });
    
    // Add event listener for ticketing type change
    $(".ticketing-input").on("change", function() {
      const isPaid = $(this).val() === "Paid";
      const $crewDiscountSection = $crewDiscountCheckbox.closest(".flex.flex-col.gap-4.w-full.bg-white");
      
      if (isPaid) {
        $crewDiscountSection.fadeIn(300);
      } else {
        $crewDiscountSection.fadeOut(300);
        $crewDiscountCheckbox.prop("checked", false);
        $crewDiscountDetails.hide();
        $crewDiscountDetails.css("opacity", "0");
        
        // Clear any validation errors
        $("#crew-size-error, #discount-error").addClass("hidden");
        $("#crew-size-input, #crew-percentage-input").removeClass("border-red-500");
      }
      
      validateAll();
    });
    
    // Add unsaved changes warning
    let formChanged = false;
    
    $form.find("input, textarea, select").on("change", function() {
      formChanged = true;
    });
    
    // Check for unsaved changes when leaving the page
    window.addEventListener("beforeunload", function(e) {
      if (formChanged) {
        const message = "You have unsaved changes. Are you sure you want to leave this page?";
        e.returnValue = message;
        return message;
      }
    });
    
    // Trigger the change event on page load to set the initial state
    $(".ticketing-input").trigger("change");
  });
  