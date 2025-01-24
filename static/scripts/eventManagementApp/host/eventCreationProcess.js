$(document).ready(function () {
  // Initialize error messages
  $("#building-error, #street-error, #apt-error, #city-error, #zip-error").hide();

  // Initialize crew discount details
  const crewDiscountCheckbox = $("#id_crew_discount");
  const crewDiscountDetails = $("#crewInfoRow");

  function toggleCrewDiscountDetails() {
    crewDiscountDetails.css(
      "display",
      crewDiscountCheckbox.is(":checked") ? "block" : "none"
    );
  }

  // $(document).find(".title-input").on("input", function () {
  //   const len = $(this).val().length;
  //   const titleError = $("#title-error");
  //   if (len < 4) {
  //     isValid = false;
  //     titleError.text("Title needs to be longer.").removeClass("hidden");
  //     $(this).css("border-color", "red");
  //   } else if (len > 100) {
  //     isValid = false;
  //     titleError.text("Title needs to be shorter.").removeClass("hidden");
  //     $(this).css("border-color", "red");
  //   } else {
  //     titleError.addClass("hidden");
  //     $(this).css("border-color", "");
  //   }
  // });

  // Initial state for crew discount
  toggleCrewDiscountDetails();

  // Add event listener for crew discount changes
  crewDiscountCheckbox.on("change", toggleCrewDiscountDetails);
  crewDiscountCheckbox.on("change", validateFields);

  // Bind input events to trigger validation
  $(".building-input, .street-input, .apt-input, .city-input, .zip-input").on("input", function () {
    validateFields();
  });

  // Debounce reference (optional)
  let debounceTimer;
  $("input, textarea, select").on("input change", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => validateFields(), 100);
  });

  validateFields();

  $("#photo-input").on("change", function () {
    validateFields();
  });

  // Quill editor change => validate
  quill.on("text-change", function () {
    validateFields();
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        // Check if this cookie string begins with the name we want
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function validateFields() {
    let isValid = true;

    // Check required fields for empty
    $(document).find("input, textarea, select").each(function () {
      if ($(this).prop("required") && !$(this).val()) {
        isValid = false;
      }
    });

    // Validate Title
    $(document).find(".title-input").each(function () {
      const len = $(this).val().length;
      const titleError = $("#title-error");
      if (len < 4) {
        isValid = false;
        titleError.text("Title needs to be longer.").removeClass("hidden");
        $(this).css("border-color", "red");
      } else if (len > 100) {
        isValid = false;
        titleError.text("Title needs to be shorter.").removeClass("hidden");
        $(this).css("border-color", "red");
      } else {
        titleError.addClass("hidden");
        $(this).css("border-color", "");
      }
    });

    // Validate Event Type
    $(document).find(".event-type-input").each(function () {
      const eventType = $(this).val();
      const eventTypeError = $("#event-type-error");;
      if (eventType == "") {
        isValid = false;
        eventTypeError.removeClass("hidden");
        $(this).css("border-color", "red");
      } else {
        eventTypeError.addClass("hidden");
        $(this).css("border-color", "");
      }
    });

    // Validate Date
    $(document).find(".date-input").each(function () {
      const len = $(this).val().length;
      const selectedDate = new Date($(this).val());
      const currentDate = new Date();
      const futureLimitDate = new Date(currentDate);

      // set future limit to 1 year from now
      futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
      // set current date to "yesterday" to avoid partial day confusion
      currentDate.setHours(-24, 0, 0, 0);

      if (len == 0) {
        $("#date-error")
          .text("Please enter a date.")
          .removeClass("hidden");
        $(this).css("border-color", "red");
      } else if (selectedDate.getTime() < currentDate.getTime()) {
        isValid = false;
        $("#date-error")
          .text("Date cannot be in the past.")
          .removeClass("hidden");
        $(this).css("border-color", "red");
      } else if (selectedDate.getTime() > futureLimitDate.getTime()) {
        isValid = false;
        $("#date-error")
          .text("Date cannot be more than a year into the future.")
          .removeClass("hidden");
        $(this).css("border-color", "red");
      } else {
        $("#date-error").addClass("hidden");
        $(this).css("border-color", "");
      }
    });

    // Validate Start/End Time
    $(document).find(".start-time-input, .end-time-input").each(function () {
      const startTime = $(".start-time-input").val();
      const endTime = $(".end-time-input").val();

      if (startTime.length === 0 || endTime.length === 0) {
        $("#time-error").hide();
      } else {
        const today = new Date();
        const start = new Date(today.toDateString() + " " + startTime);
        let end = new Date(today.toDateString() + " " + endTime);

        // If end is earlier than start, assume it's the next day
        if (end < start) {
          end.setHours(end.getHours() + 24);
        }

        const hourDifference = (end - start) / (1000 * 60 * 60);

        if (hourDifference > 12) {
          isValid = false;
          $("#time-error").show();
        } else {
          $("#time-error").hide();
        }
      }
    });

    // Validate Quill (Description)
    const contentLength = quill.getText().trim().length;
    if (contentLength === 0) {
      $("#body-error").hide();
    } else if (contentLength < 10) {
      isValid = false;
      $("#body-error").text("Description needs to be longer.").show();
    } else if (contentLength > 5000) {
      isValid = false;
      $("#body-error").text("Description needs to be shorter.").show();
    } else {
      $("#body-error").hide();
    }

    // Validate Building
    $(document).find(".building-input").each(function () {
      const len = $(this).val().length;
      if (len === 0) {
        $("#building-error").hide();
      } else if (len > 100) {
        isValid = false;
        $("#building-error").show();
      } else {
        $("#building-error").hide();
      }
    });

    // Validate Street
    $(document).find(".street-input").each(function () {
      const len = $(this).val().length;
      if (len === 0) {
        $("#street-error").hide();
      } else if (len > 100) {
        isValid = false;
        $("#street-error").show();
      } else {
        $("#street-error").hide();
      }
    });

    // Validate Apt
    $(document).find(".apt-input").each(function () {
      const len = $(this).val().length;
      if (len === 0) {
        $("#apt-error").hide();
      } else if (len > 100) {
        isValid = false;
        $("#apt-error").show();
      } else {
        $("#apt-error").hide();
      }
    });

    // Validate City
    $(document).find(".city-input").each(function () {
      const len = $(this).val().length;
      if (len === 0) {
        $("#city-error").hide();
      } else if (len > 50) {
        isValid = false;
        $("#city-error").show();
      } else {
        $("#city-error").hide();
      }
    });

    // Validate ZIP
    $(document).find(".zip-input").each(function () {
      const len = $(this).val().length;
      if (len === 0) {
        $("#zip-error").hide();
      } else if (len < 5) {
        isValid = false;
        $("#zip-error").show();
      } else {
        $("#zip-error").hide();
      }
    });

    // Validate Header Photo
    $(document).find("#photo-input").each(function () {
      const headerPhotoInput = document.getElementById("photo-input");
      if (!headerPhotoInput.files.length) {
        isValid = false;
      }
    });

    // Validate crew discount fields if discount is checked
    if (crewDiscountCheckbox.is(":checked")) {
      const minCrewSize = $("#crew-size-input").val();
      const discountPercentage = $("#crew-percentage-input").val();

      if (!minCrewSize || minCrewSize > 100 || minCrewSize < 2) {
        isValid = false;
        $("#crew-size-error").removeClass("hidden");
        $("#crew-size-input").css("border-color", "red");
      } else {
        $("#crew-size-error").addClass("hidden");
        $("#crew-size-input").css("border-color", "");
      }
      
      if (!discountPercentage || discountPercentage <= 0 || discountPercentage > 100) {
        isValid = false;
        $("#discount-error").removeClass("hidden");
        $("#crew-percentage-input").css("border-color", "red");
      } else {
        $("#discount-error").addClass("hidden");
        $("#crew-percentage-input").css("border-color", "");
      }
    } else {
      // If crew discount is not checked, fields are valid by default
      $("#crew-size-error").addClass("hidden");
      $("#discount-error").addClass("hidden");
      $("#crew-size-input").css("border-color", "");
      $("#crew-percentage-input").css("border-color", "");
    }

    if(isValid) {
      $("#submitBtn").removeClass("hidden");
      $("#cannotSubmit").addClass("hidden");
    } else {
      $("#submitBtn").addClass("hidden");
      $("#cannotSubmit").removeClass("hidden");
    }
  }
});
