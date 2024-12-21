$(document).ready(function () {
    let debounceTimer;
    let idName;
    
     // Add this event handler
    $(document).on('click', '.gradient-btn', function() {
            sendConnectRequest(this);
    });

        
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
   
    function sendConnectRequest(button) {
        const username = button.dataset.username;
        
        $.ajax({
            url: '/send-connect-request/',  // You'll need to create this endpoint
            method: 'POST',
            data: {
                'action': 'send_request',
                'socketUsername': username,
                'csrfmiddlewaretoken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            success: function(response) {
                if (response.status === 'success') {
                    // Update button state
                    button.textContent = 'Pending';
                    button.classList.add('pending');
                    // You might want to disable the button or change its appearance
                }
            },
            error: function(xhr, status, error) {
                console.error('Error sending connect request:', error);
            }
        });
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
                        $.each(data.results, function (index, item) {
                            let resultHtml = '';
                            if (item.eventId) {
                                // Render event
                                resultHtml = `
                                    <a href="/event/${item.eventId}/" class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
                                        <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
                                            <img src="${item.header_photo_url}" alt="" class="lazyload w-full h-[448px] rounded-2xl rounded-b-none object-cover">
                                        </div>
                                        <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
                                            <h2 class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-2xl">${item.title}</h2>
                                            <div class="eventSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                                                <p class="flex flex-row justify-start">Hosted by @${item.host_username}</p>
                                                <p class="w-full flex justify-end font-Wanted-Bold text-Large">${item.date}</p>
                                            </div>
                                        </div>
                                    </a>`;
                            } else if (item.username) {
                                // Render user
                                resultHtml = `
                                    <div class="category-user-card hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
                                        <div class="user-image w-full rounded-2xl shadow-custom-shadow-3">
                                            <img src="${item.profile_photo_url}" alt="${item.display_name}" class="lazyload w-full h-[448px] rounded-2xl object-cover">
                                        </div>
                                        <div class="category-user-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
                                            <h2 class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-2xl">${item.display_name}</h2>
                                            <div class="userSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                                                <p class="flex flex-row justify-start">@${item.username}</p>
                                            </div>
                                                      <!-- Connect Button -->
                          <button class="gradient-btn cursor-pointer text-Pre-Xl md:text-xl hover:bg-green" 
        type="button" 
        role="button"
        data-username="${item.username}">
        Connect
    </button>
                                        </div>
                                    </div>`;
                            }
                            fragment.append(resultHtml);
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
