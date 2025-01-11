$(document).ready(function () {
  $("#collegeSearchBar").on("click", function () {
    $("#collegeSearchCardModal").show();
  });

  $("#closeSearchModalButton").on("click", function () {
    $("#collegeSearchCardModal").hide();
    $(".searchCardBody").empty();
    $("#collegeSearchContentBar").val("");
  });

  $(document).keydown(function (event) {
    if (event.key == "Escape") {
      $("#collegeSearchCardModal").hide();
      $(".searchCardBody").empty();
      $("#collegeSearchContentBar").val("");
    }
  });

  $(document).click(function (event) {
    if (
      !$(event.target).closest("#find-colleges").length &&
      !$(event.target).closest(".searchCard").length
    ) {
      $("#collegeSearchCardModal").hide();
      $(".searchCardBody").empty();
      $("#collegeSearchContentBar").val("");
    }
  });

  $("#collegeSearchContentBar").on("input", function () {
    var query = $(this).val();
    var crewId = $("#crew-data").data("crew-id");

    if (query.trim() === "") {
      // If the search bar is empty, clear the results
      $(".searchCardBody").empty();
    } else {
      // If the search bar has input, perform the search
      $.ajax({
        url: "/social/crew/" + crewId + "/",
        data: {
          query: query,
        },
        dataType: "json",
        success: function (data) {
          $(".searchCardBody").empty(); 

          
          if (data.no_results) {
            $(".searchCardBody").html(data.no_results_html);
          } else {
            console.log(data.results_html);
            // Append each result to the search card body
            $.each(data.results_html, function (index, resultHtml) {
              $(".searchCardBody").append(resultHtml);
            });
          }

          $("#collegeSearchCardModal").show(); // Show modal with results
        },
      });
    }
  });
});
