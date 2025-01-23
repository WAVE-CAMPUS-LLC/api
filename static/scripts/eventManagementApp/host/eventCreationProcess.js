$(document).ready(function () {
    // Initialize error messages
    $(
      "#building-error, #street-error, #apt-error, #city-error, #zip-error"
    ).hide();
  
    // Initialize crew discount details
    const crewDiscountCheckbox = $("#id_crew_discount");
    const crewDiscountDetails = $("#crew-discount-details");
  
    function toggleCrewDiscountDetails() {
      crewDiscountDetails.css(
        "display",
        crewDiscountCheckbox.is(":checked") ? "flex" : "none"
      );
    }
  
    // Initial state for crew discount
    toggleCrewDiscountDetails();
  
    // Add event listener for crew discount changes
    crewDiscountCheckbox.on("change", toggleCrewDiscountDetails);
  
    // Add input event listeners for all address fields
    $(".building-input, .street-input, .apt-input, .city-input, .zip-input").on(
      "input",
      function () {
        validate$(document)();
      }
    );
    
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
  
      $(document).find("input, textarea, select").each(function () {
        if ($(this).prop("required") && !$(this).val()) {
          isValid = false;
        }
      });
  
      $(document).find(".text-input").each(function () {
        const len = $(this).val().length;
        const titleError = $("#title-error");
        if (len === 0) {
          titleError.addClass("hidden");
          console.log("Title is empty, hiding error.");
        } else if (len < 4) {
          isValid = false;
          titleError.text("Title needs to be longer.").removeClass("hidden");
          console.log("Title too short, showing error.");
        } else if (len > 100) {
          isValid = false;
          titleError.text("Title needs to be shorter.").removeClass("hidden");
          console.log("Title too long, showing error.");
        } else {
          titleError.addClass("hidden");
          console.log("Title length is valid, hiding error.");
        }
      });
      $(document).find(".date-input").each(function () {
        const len = $(this).val().length;
        const selectedDate = new Date($(this).val());
        const currentDate = new Date();
        const futureLimitDate = new Date(currentDate);

        futureLimitDate.setFullYear(currentDate.getFullYear() + 1);
        currentDate.setHours(-24, 0, 0, 0);

        if (len == 0) {
          $("#date-error").addClass("hidden");
        } else if (selectedDate.getTime() < currentDate.getTime()) {
          isValid = false;
          $("#date-error")
            .text("Date cannot be in the past.")
            .removeClass("hidden");
        } else if (selectedDate.getTime() > futureLimitDate.getTime()) {
          isValid = false;
          $("#date-error")
            .text("Date cannot be in more than a year into the future.")
            .removeClass("hidden");
        } else {
          $("#date-error").addClass("hidden");
        }
      });
      $(document).find(".start-time-input").each(function () {
        const startTime = $(".start-time-input").val();
        const endTime = $(".end-time-input").val();

        if (startTime.length === 0 || endTime.length === 0) {
          $("#time-error").hide();
        } else {
          const today = new Date();
          const start = new Date(today.toDateString() + " " + startTime);
          let end = new Date(today.toDateString() + " " + endTime);

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
      const contentLength = quill.getText().trim().length; // Use Quill content
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
      $(document).find(".building-input").each(function () {
        const len = $(this).val().length;
        console.log("Building input length:", len);

        if (len === 0) {
          $("#building-error").hide();
        } else if (len > 100) {
          isValid = false;
          $("#building-error").show();
        } else {
          $("#building-error").hide();
        }
      });

      $(document).find(".street-input").each(function () {
        const len = $(this).val().length;
        console.log("Street input length:", len);

        if (len === 0) {
          $("#street-error").hide();
        } else if (len > 100) {
          isValid = false;
          $("#street-error").show();
        } else {
          $("#street-error").hide();
        }
      });

      $(document).find(".apt-input").each(function () {
        const len = $(this).val().length;
        console.log("Apt input length:", len);

        if (len === 0) {
          $("#apt-error").hide();
        } else if (len > 100) {
          isValid = false;
          $("#apt-error").show();
        } else {
          $("#apt-error").hide();
        }
      });

      $(document).find(".city-input").each(function () {
        const len = $(this).val().length;
        console.log("City input length:", len);

        if (len === 0) {
          $("#city-error").hide();
        } else if (len > 50) {
          isValid = false;
          $("#city-error").show();
        } else {
          $("#city-error").hide();
        }
      });

      $(document).find(".zip-input").each(function () {
        const len = $(this).val().length;
        console.log("Zip input length:", len);

        if (len === 0) {
          $("#zip-error").hide();
        } else if (len < 5) {
          isValid = false;
          $("#zip-error").show();
        } else {
          $("#zip-error").hide();
        }
      });
      $(document).find("#photo-input").each(function () {
        const headerPhotoInput = document.getElementById("photo-input");
        if (!headerPhotoInput.files.length) {
          isValid = false;
        }
      });
        // Validate crew discount fields
      if (
        $(document)
          .find("#" + eventForm.crew_discount.auto_id)
          .is(":checked")
      ) {
        const minCrewSize = $(document)
          .find("#" + eventForm.minimum_crew_size.auto_id)
          .val();
        const discountPercentage = $(document)
          .find("#" + eventForm.crew_discount_percentage.auto_id)
          .val();

        if (!minCrewSize || minCrewSize < 2) {
          isValid = false;
          $("#crew-size-error").removeClass("hidden");
        } else {
          $("#crew-size-error").addClass("hidden");
        }

        if (
          !discountPercentage ||
          discountPercentage <= 0 ||
          discountPercentage > 100
        ) {
          isValid = false;
          $("#discount-error").removeClass("hidden");
        } else {
          $("#discount-error").addClass("hidden");
        }
      } else {
        // If crew discount is not checked, fields are valid
        $("#crew-size-error").addClass("hidden");
        $("#discount-error").addClass("hidden");
      }
  }
  
  $("input, textarea, select").on("input change", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => validateFields(), 100);
  });

  $("#photo-input").on("change", function () {
    validateFields();
  });

  quill.on("text-change", function () {
    validateFields();
  });
});
