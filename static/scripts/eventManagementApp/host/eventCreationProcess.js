$(document).ready(function () {
  // Cache selectors for better performance
  var $crewDiscountCheckbox = $("#id_crew_discount");
  var $crewDiscountDetails = $("#crewInfoRow");
  var $form = $("#eventForm");
  var $submitBtn = $("#submitBtn");
  var $cannotSubmit = $("#cannotSubmit");

  // Function to show or hide error messages and set border color
  function toggleError(selector, show, message) {
    var $error = $(selector);
    if (show) {
      $error.text(message).removeClass("hidden");
    } else {
      $error.addClass("hidden");
    }
  }

  // Function to set border color based on validation
  function setBorder(element, isError) {
    $(element).css("border-color", isError ? "red" : "");
  }

  // Validation rules mapped by input class
  var validationRules = {
    ".title-input": {
      required: true,
      maxLength: 100,
      errorSelector: "#title-error",
      errorMessages: {
        required: "Please enter a title",
        maxLength: "Title needs to be shorter",
      },
    },
    ".event-type-input": {
      required: true,
      errorSelector: "#event-type-error",
      errorMessages: {
        required: "Please choose an option",
      },
    },
    ".date-input": {
      required: true,
      validate: function (value) {
        var selectedDate = new Date(value);
        var currentDate = new Date();
        var futureLimitDate = new Date(currentDate);
        futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
        currentDate.setHours(-24, 0, 0, 0);

        if (selectedDate < currentDate) {
          return "Date cannot be in the past";
        }
        if (selectedDate > futureLimitDate) {
          return "Date cannot be more than a year into the future";
        }
        return "";
      },
      errorSelector: "#date-error",
      errorMessages: {
        required: "Please enter a date",
      },
    },
    ".start-time-input": {
      required: true,
      errorSelector: "#time-error",
      errorMessages: {
        required: "Please enter start time",
      },
    },
    ".end-time-input": {
      required: true,
      errorSelector: "#time-error",
      errorMessages: {
        required: "Please enter end time",
      },
    },
    ".event-visibility-input": {
      required: true,
      errorSelector: "#visibility-error",
      errorMessages: {
        required: "Please choose an option",
      },
    },
    ".ticket-type-input": {
      required: true,
      errorSelector: "#ticket-type-error",
      errorMessages: {
        required: "Please choose an option",
      },
    },
    ".building-input": {
      required: false,
      maxLength: 100,
      errorSelector: "#building-error",
      errorMessages: {
        maxLength: "Building name needs to be shorter",
      },
    },
    ".street-input": {
      required: true,
      maxLength: 100,
      errorSelector: "#street-error",
      errorMessages: {
        required: "Please enter a street",
        maxLength: "Street needs to be shorter",
      },
    },
    ".apt-input": {
      required: false,
      maxLength: 50,
      errorSelector: "#apt-error",
      errorMessages: {
        maxLength: "Apt needs to be shorter",
      },
    },
    ".city-input": {
      required: true,
      errorSelector: "#city-error",
      errorMessages: {
        required: "Please enter a city/town",
      },
    },
    ".state-input": {
      required: true,
      errorSelector: "#state-error",
      errorMessages: {
        required: "Please choose an option",
      },
    },
    ".zip-input": {
      required: true,
      minLength: 5,
      errorSelector: "#zip-error",
      errorMessages: {
        required: "Please enter a ZIP code",
        minLength: "ZIP code needs to be longer",
      },
    },
  };

  // Function to validate individual field
  function validateField($field, rules) {
    var value = $field.val().trim();
    var isError = false;
    var errorMessage = "";

    if (rules.required && !value) {
      isError = true;
      errorMessage = rules.errorMessages.required;
    }

    if (!isError && rules.maxLength && value.length > rules.maxLength) {
      isError = true;
      errorMessage = rules.errorMessages.maxLength;
    }

    if (!isError && rules.minLength && value.length < rules.minLength) {
      isError = true;
      errorMessage = rules.errorMessages.minLength;
    }

    if (!isError && typeof rules.validate === "function") {
      var customError = rules.validate(value);
      if (customError) {
        isError = true;
        errorMessage = customError;
      }
    }

    toggleError(rules.errorSelector, isError, errorMessage);
    setBorder($field, isError);

    return !isError;
  }

  // Function to validate time fields together
  function validateTimeFields() {
    var startTime = $(".start-time-input").val();
    var endTime = $(".end-time-input").val();
    var isValid = true;

    if (!startTime || !endTime) {
      toggleError("#time-error", true, "Invalid Time");
      $(".start-time-input, .end-time-input").css("border-color", "red");
      isValid = false;
    } else {
      toggleError("#time-error", false, "");
      $(".start-time-input, .end-time-input").css("border-color", "");
    }

    return isValid;
  }

  // Function to validate all fields
  function validateFields() {
    var isValid = true;

    // Validate each field based on validationRules
    $.each(validationRules, function (selector, rules) {
      // console.log("Validating selector:", selector, "Rules:", rules); // Debugging log
      $(selector).each(function () {
        var $field = $(this);
        var fieldValid = validateField($field, rules);
        if (!fieldValid) {
          isValid = false;
        }
      });
    });

    // Special handling for time fields
    var timeValid = validateTimeFields();
    if (!timeValid) {
      isValid = false;
    }

    // Validate Quill description
    if (typeof quill !== "undefined" && quill instanceof Quill) {
      var contentLength = quill.getText().trim().length;
      if (contentLength === 0) {
        isValid = false;
        toggleError("#body-error", true, "Please enter a description");
        $(".ql-container").css("border-color", "red");
      } else if (contentLength > 5000) {
        isValid = false;
        toggleError("#body-error", true, "Description needs to be shorter");
        $(".ql-container").css("border-color", "red");
      } else {
        toggleError("#body-error", false, "");
        $(".ql-container").css("border-color", "");
      }
    }

    // Additional validation for crew discount if checked
    if ($crewDiscountCheckbox.is(":checked")) {
      var minCrewSize = $("#crew-size-input").val();
      var discountPercentage = $("#crew-percentage-input").val();
      var crewValid = true;

      if (!minCrewSize || minCrewSize < 2 || minCrewSize > 100) {
        crewValid = false;
        toggleError("#crew-size-error", true, "Invalid Crew Size");
        $("#crew-size-input").css("border-color", "red");
      } else {
        toggleError("#crew-size-error", false);
        $("#crew-size-input").css("border-color", "");
      }

      if (
        !discountPercentage ||
        discountPercentage <= 0 ||
        discountPercentage > 100
      ) {
        crewValid = false;
        toggleError("#discount-error", true, "Invalid Discount Percentage");
        $("#crew-percentage-input").css("border-color", "red");
      } else {
        toggleError("#discount-error", false);
        $("#crew-percentage-input").css("border-color", "");
      }

      if (!crewValid) {
        isValid = false;
      }
    } else {
      // Reset crew discount errors if not checked
      toggleError("#crew-size-error", false);
      toggleError("#discount-error", false);
      $("#crew-size-input, #crew-percentage-input").css("border-color", "");
    }

    // Validate Header Photo
    var headerPhoto = $("#photo-input")[0].files.length > 0;
    if (!headerPhoto) {
      isValid = false;
      toggleError("#photo-error", true, "Please upload a header photo");
      $("#photo-input").css("border-color", "red");
    } else {
      toggleError("#photo-error", false);
      $("#photo-input").css("border-color", "");
    }

    // Toggle submit buttons
    if (isValid) {
      $submitBtn.show();
      $cannotSubmit.hide();
    } else {
      $submitBtn.hide();
      $cannotSubmit.show();
    }
  }

  // Function to toggle crew discount details
  function toggleCrewDiscountDetails() {
    $crewDiscountDetails.toggle($crewDiscountCheckbox.is(":checked"));
  }

  // Initialize crew discount display and bind events
  toggleCrewDiscountDetails();
  $crewDiscountCheckbox.on("change", function () {
    toggleCrewDiscountDetails();
    validateFields();
  });

  // Debounce function to limit the rate of function calls
  function debounce(func, delay) {
    var timer;
    return function () {
      var context = this;
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () {
        func.apply(context, args);
      }, delay);
    };
  }

  // Bind input and change events with debouncing
  $form
    .find("input, textarea, select")
    .on("input change", debounce(validateFields, 100));

  // Specific event bindings
  $("#photo-input").on("change", validateFields);

  // Initialize Quill editor (assuming it's initialized elsewhere)
  if (typeof quill !== "undefined" && quill instanceof Quill) {
    quill.on("text-change", validateFields);
  }

  // Initial validation
  validateFields();
});
