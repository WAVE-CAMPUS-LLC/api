$(document).ready(function () {
    let debounceTimer;
    let idName;

    $('#search-events-input-large').on('input', function () {
        idName = 'large';
        handleEmptyInput(idName); // Check and hide results if input is empty immediately
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            performSearch(idName); // Perform the search with debounce
        }, 300); // Adjust delay as needed
    });

    $(document).on('click', function (e) {
        // Iterate over both 'large' and 'mobile' to handle both cases
        ['large', 'mobile'].forEach(idName => {
            const $searchContainer = $(`#main-find-events`);
            const $searchResults = $(`#events-search-results-${idName}`);
    
            if (!$(e.target).closest($searchContainer).length) {
                $searchResults.addClass('hidden').fadeOut(300);
            }
        });
    });
    

    $(document).on('keydown', function (e) {
        if (e.key === 'Escape') {
            $('#events-search-results-large, #events-search-results-mobile').addClass('hidden').fadeOut(300);
        }
    });

    $('#search-events-input-mobile').on('input', function () {
        idName = 'mobile';
        handleEmptyInput(idName); // Check and hide results if input is empty immediately
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () {
            performSearch(idName); // Perform the search with debounce
        }, 300); // Adjust delay as needed
    });

    function handleEmptyInput(idName) {
        // Immediately handle empty input to hide results
        var query = $(`#search-events-input-${idName}`).val().trim();
        if (query.length === 0) {
            $(`#events-search-items-${idName}`).empty();
            $(`#events-search-results-${idName}`).addClass('hidden').fadeOut(300);
        }
    }

    function showLoadingNotice(idName) {
        // Show loading state immediately when user types
        $(`#events-search-items-${idName}`).html(`<div id="loading-events-notice" class="flex justify-center py-5">
            <h3 class="font-Wanted-ExtraBold text-[40px] text-center">Loading events...</h3>
        </div>`);
    }

    function performSearch(idName) {
        var query = $(`#search-events-input-${idName}`).val().trim();
        showLoadingNotice(idName);
        if (query.length > 0) {
            $(`#event-search-results-${idName}`).removeClass('hidden').fadeIn(300); // Smoothly show results

            // Perform AJAX search
            $.ajax({
                url: 'search/',
                data: { 'searchEvents': query },
                dataType: 'json',
                success: function (data) {
                    let fragment = $(document.createDocumentFragment()); // Use DocumentFragment for smoother updates
                    $(`#events-search-items-${idName}`).empty(); // Clear previous results

                    if (data.results && data.results.length > 0) {
                        // Append each result to the fragment
                        $.each(data.results, function (index, event) {
                            let resultHtml = `
                                <a href="/event/${event.eventId}/" class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
                                    <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
                                        <img src="${event.header_photo_url}" data-src="${event.header_photo_url}" alt="" class="lazyload w-full h-[448px] rounded-2xl rounded-b-none object-cover">
                                    </div>
                                    <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
                                        <h2 id="eventTitle" class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-2xl">${event.title}</h2>
                                        <div class="eventSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                                            <p id="eventHost" class="flex flex-row justify-start">Hosted by @${event.host_username}</p>
                                            <p id="eventDate" class="w-full flex justify-end font-Wanted-Bold text-Large">${event.date}</p>
                                        </div>
                                    </div>
                                </a>`;
                            fragment.append(resultHtml); // Add each result to the fragment
                        });

                        $(`#events-search-items-${idName}`).append(fragment); // Update DOM once with the fragment
                    } else {
                        $(`#events-search-items-${idName}`).html(`<div id="loading-events-notice" class="flex justify-center py-5">
                            <h3 class="font-Wanted-ExtraBold text-[40px] text-center">No event found</h3>
                        </div>`);
                    }
                },
                error: function () {
                    $(`#events-search-items-${idName}`).html('<p class="error-message">Failed to fetch events. Please try again.</p>');
                }
            });
        } else {
            // If query is empty, hide the results container immediately
            $(`#events-search-items-${idName}`).empty();
            $(`#events-search-results-${idName}`).addClass('hidden').fadeOut(300);
        }
    }
});
