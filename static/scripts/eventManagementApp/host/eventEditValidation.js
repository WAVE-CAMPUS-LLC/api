$(function () {
    // Cache selectors for performance
    var $form = $("#eventForm");
    var $submitBtn = $("#submitBtn");
    var $cannotSubmit = $("#cannotSubmit");
    var $crewDiscountCheckbox = $("#id_crew_discount"); // Assumes auto_id "id_crew_discount"
    var $crewDiscountDetails = $("#crewInfoRow");
    var touchedFields = {};
  
    // Validation rules configuration
    var validationRules = {
      ".title-input": {
        required: true,
        maxLength: 100,
        errorSelector: "#title-error",
        messages: {
          required: "Please enter a title",
          maxLength: "Title needs to be shorter"
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
          var selectedDate = new Date(value),
              currentDate = new Date(),
              futureLimitDate = new Date(currentDate);
          futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
          currentDate.setHours(0, 0, 0, 0);
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
      $el.css("border-color", isError ? "red" : "");
    }
  
    function validateField($field, rules) {
      var value = $field.val().trim();
      var isValid = true;
      var errorMsg = "";
      if (rules.required && !value) {
        isValid = false;
        errorMsg = rules.messages.required;
      }
      if (isValid && rules.maxLength && value.length > rules.maxLength) {
        isValid = false;
        errorMsg = rules.messages.maxLength;
      }
      if (isValid && rules.minLength && value.length < rules.minLength) {
        isValid = false;
        errorMsg = rules.messages.minLength;
      }
      if (isValid && typeof rules.validate === "function") {
        var customError = rules.validate(value);
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
        } else {
          hideError(rules.errorSelector);
          setBorder($field, false);
        }
      }
      return isValid;
    }
  
    function validateTimeFields() {
      var startTime = $(".start-time-input").val(),
          endTime = $(".end-time-input").val(),
          valid = true;
      if (!startTime || !endTime) {
        showError("#time-error", "Invalid Time");
        $(".start-time-input, .end-time-input").css("border-color", "red");
        valid = false;
      } else {
        hideError("#time-error");
        $(".start-time-input, .end-time-input").css("border-color", "");
      }
      return valid;
    }
  
    function validateQuill() {
      if (typeof quill !== "undefined" && quill instanceof Quill) {
        var text = quill.getText().trim();
        if (text.length === 0) {
          showError("#body-error", "Please enter a description");
          $(".ql-container").css("border-color", "red");
          return false;
        } else if (text.length > 5000) {
          showError("#body-error", "Description needs to be shorter");
          $(".ql-container").css("border-color", "red");
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
        var minCrew = parseInt($("#crew-size-input").val(), 10),
            discount = parseFloat($("#crew-percentage-input").val()),
            valid = true;
        if (!minCrew || minCrew < 2 || minCrew > 100) {
          showError("#crew-size-error", "Invalid Crew Size");
          $("#crew-size-input").css("border-color", "red");
          valid = false;
        } else {
          hideError("#crew-size-error");
          $("#crew-size-input").css("border-color", "");
        }
        if (!discount || discount <= 0 || discount > 100) {
          showError("#discount-error", "Invalid Discount Percentage");
          $("#crew-percentage-input").css("border-color", "red");
          valid = false;
        } else {
          hideError("#discount-error");
          $("#crew-percentage-input").css("border-color", "");
        }
        return valid;
      } else {
        hideError("#crew-size-error");
        hideError("#discount-error");
        $("#crew-size-input, #crew-percentage-input").css("border-color", "");
        return true;
      }
    }
  
    function validateHeaderPhoto() {
      var hasPhoto = $("#photo-input")[0].files.length > 0;
      if (!hasPhoto) {
        showError("#photo-error", "Please upload a header photo");
        $("#photo-input").css("border-color", "red");
        return false;
      } else {
        hideError("#photo-error");
        $("#photo-input").css("border-color", "");
        return true;
      }
    }
  
    function validateAll() {
      var overallValid = true;
      // Validate each field defined in validationRules
      $.each(validationRules, function (selector, rules) {
        $(selector).each(function () {
          if (!validateField($(this), rules)) {
            overallValid = false;
            return false;
          }
        });
        if (!overallValid) return false;
      });
      if (!validateTimeFields()) overallValid = false;
      if (!validateQuill()) overallValid = false;
      if (!validateCrewDiscount()) overallValid = false;
      if (!validateHeaderPhoto()) overallValid = false;
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
      if (!validateAll()) {
        e.preventDefault();
        alert("Please correct the errors in the form before submitting.");
      }
    });
  });
  