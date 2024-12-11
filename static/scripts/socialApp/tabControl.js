$(document).ready(function () {
  $("#deleteCrew").on("click", function () {
    $("#postDeleteCrewConfirm").show();
    $("#postDeleteCrewCancel").show();
    $("#postDeleteCrewText").show();
    $("#deleteCrew").hide();
  });

  $("#cancelDelete").on("click", function () {
    $("#deleteCrew").show();
    $("#postDeleteCrewConfirm").hide();
    $("#postDeleteCrewCancel").hide();
    $("#postDeleteCrewText").hide();
  });

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
          $(".searchCardBody").empty(); // Clear previous results

          // Append each result to the search card body
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

document.addEventListener("DOMContentLoaded", function () {
  // Function to handle tab click
  function handleTabClick(tab, tabContents, tabActiveName) {
    tab.forEach((tab) => {
      tab.classList.remove(tabActiveName);
    });
    this.classList.add(tabActiveName);

    // Logic to display corresponding content based on clicked tab
    const tabId = this.getAttribute("data-tab");
    showTabContent(tabContents, tabId);
  }

  // Function to display corresponding content based on tab clicked
  function showTabContent(contents, tabId) {
    // Hide all tab contents
    contents.forEach((content) => {
      content.style.display = "none";
    });

    // Show the selected tab content
    const selectedTabContent = document.getElementById(tabId);
    if (selectedTabContent) {
      selectedTabContent.style.display = "block";
    }
  }

  // Initialize tab systems for each body section
  initializeTabSystem("socialBody", "social-tab", "social-home-elements", 'social-tab-active');
  initializeTabSystem("pageBody", "crewDetailsTab", "crewTabInformation", 'crew-tab-active');

  // Function to initialize tab system for a specific body section
  function initializeTabSystem(bodyId, tabClass, contentClass, tabActiveName) {
    const tabs = document.querySelectorAll(`#${bodyId} .${tabClass}`);
    const tabContents = document.querySelectorAll(
      `#${bodyId} .${contentClass}`
    );

    tabs.forEach((tab) => {
      tab.addEventListener("click", function () {
        handleTabClick.call(this, tabs, tabContents, tabActiveName);
      });
    });

    if (tabContents.length > 0) {
      tabContents[0].style.display = "block";
    }

    // Set the first tab as active by default in each body section
    if (tabs.length > 0) {
      tabs[0].classList.add(tabActiveName);
      const defaultTabId = tabs[0].getAttribute("data-tab");
      showTabContent(tabContents, defaultTabId);
    }
  }
});
