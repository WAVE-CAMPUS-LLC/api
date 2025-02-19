$(document).ready(function () {
    let debounceTimer;

    // Unified input handler
    $(document).on('input', '.search-input', function () {
        const context = $(this).data('context'); // 'event' or 'friend'
        const idName = $(this).data('id'); // 'large' or 'mobile'

        handleEmptyInput(context, idName); // Handle empty input immediately
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            performSearch(context, idName); // Perform search with debounce
        }, 300);
    });

    // Handle clicking outside search results
    $(document).on('click', function (e) {
        ['large', 'mobile'].forEach(idName => {
            const $searchContainer = $(`#main-find-${idName}`);
            const $searchResults = $(`.search-results-${idName}`);

            if (!$(e.target).closest($searchContainer).length) {
                $searchResults.addClass('hidden').fadeOut(300);
            }
        });
    });

    $(document).on('keydown', function (e) {
        if (e.key === 'Escape') {
            $('.search-results').addClass('hidden').fadeOut(300);
        }
    });

    function handleEmptyInput(context, idName) {
        const $input = $(`.search-input[data-context=${context}][data-id=${idName}]`);
        const $items = $(`.${context}-search-items-${idName}`);
        const $results = $(`.${context}-search-results-${idName}`);

        if ($input.val().trim().length === 0) {
            $items.empty();
            $results.addClass('hidden').fadeOut(300);
        }
    }

    function showLoadingNotice(context, idName) {
        const $items = $(`.${context}-search-items-${idName}`);
        $items.html(`
            <div class="flex justify-center py-5">
                <h3 class="font-Wanted-ExtraBold text-[40px] text-center">Searching...</h3>
            </div>
        `);
    }

    function performSearch(context, idName) {
        const $input = $(`.search-input[data-context=${context}][data-id=${idName}]`);
        const query = $input.val().trim();

        if (query.length > 0) {
            const $results = $(`.${context}-search-results-${idName}`);
            $results.removeClass('hidden').fadeIn(300);
            showLoadingNotice(context, idName);

            // Determine the correct search URL based on context
            const searchUrl = context === 'event' 
                ? '/explore/search/' 
                : '/social/search/';

            $.ajax({
                url: searchUrl,
                data: { query, context },
                dataType: 'json',
                success: function(data) {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.empty();

                    if (data.results && data.results.length > 0) {
                        data.results.forEach(item => {
                            const resultHtml = context === 'event'
                                ? renderEventItem(item)
                                : renderFriendItem(item);
                            $items.append(resultHtml);
                        });
                    } else {
                        $items.html(`
                            <div class="flex justify-center py-5">
                                <h3 class="font-Wanted-ExtraBold text-[40px] text-center">No results found</h3>
                            </div>
                        `);
                    }
                },
                error: function() {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.html('<p class="error-message">Failed to fetch results. Please try again.</p>');
                }
            });
        }
    }

    function sendConnectRequest(button) {
        const username = button.dataset.username;
        const $button = $(button);
        const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

        if (!csrfToken) {
            alert('CSRF token not found. Please refresh the page and try again.');
            return;
        }

        // Disable button to prevent multiple clicks
        $button.prop('disabled', true)
               .addClass('opacity-50');

        $.ajax({
            url: '/social/send-friend-request/',
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: {
                receiver_username: username,
                csrfmiddlewaretoken: csrfToken
            },
            success: function(response) {
                if (response.status === 'success') {
                    // Update button to show cancel option
                    $button.removeClass('bg-gradient-to-r from-[#008d95bc] to-[#13c9d3] opacity-50')
                           .addClass('bg-red-600')
                           .text('Cancel Request')
                           .prop('disabled', false)
                           .removeClass('send-connect')
                           .addClass('cancel-connect');
                } else {
                    alert(response.message || 'Failed to send friend request');
                    $button.prop('disabled', false)
                           .removeClass('opacity-50');
                }
            },
            error: function(xhr) {
                let errorMessage = 'An error occurred while sending the friend request';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                }
                alert(errorMessage);
                $button.prop('disabled', false)
                       .removeClass('opacity-50');
            }
        });
    }

    function cancelConnectRequest(button) {
        const username = button.dataset.username;
        const $button = $(button);
        const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

        if (!csrfToken) {
            alert('CSRF token not found. Please refresh the page and try again.');
            return;
        }

        // Disable button to prevent multiple clicks
        $button.prop('disabled', true)
               .addClass('opacity-50');

        $.ajax({
            url: '/social/cancel-friend-request/',
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            data: {
                receiver_username: username,
                csrfmiddlewaretoken: csrfToken
            },
            success: function(response) {
                if (response.status === 'success') {
                    // Update button back to connect
                    $button.removeClass('bg-red-600 opacity-50')
                           .addClass('bg-gradient-to-r from-[#008d95bc] to-[#13c9d3]')
                           .text('Connect')
                           .prop('disabled', false)
                           .removeClass('cancel-connect')
                           .addClass('send-connect');
                } else {
                    alert(response.message || 'Failed to cancel friend request');
                    $button.prop('disabled', false)
                           .removeClass('opacity-50');
                }
            },
            error: function(xhr) {
                let errorMessage = 'An error occurred while canceling the friend request';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                }
                alert(errorMessage);
                $button.prop('disabled', false)
                       .removeClass('opacity-50');
            }
        });
    }

    // Add click handlers for connect and cancel buttons
    $(document).on('click', '.send-connect', function(e) {
        e.preventDefault();
        sendConnectRequest(this);
    });

    $(document).on('click', '.cancel-connect', function(e) {
        e.preventDefault();
        cancelConnectRequest(this);
    });

    function renderEventItem(item) {
        return `
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
    }

    function renderFriendItem(item) {
        let buttonHtml = '';
        
        if (item.is_friend) {
            buttonHtml = `
                <button class="py-2 px-5 border border-solid border-transparent text-white font-Wanted-Variable no-underline flex items-center justify-center gap-2.5 cursor-not-allowed text-[18px] rounded-[20px] bg-[#00b500]" disabled>
                    Friend
                </button>`;
        } else if (item.has_sent_friend_request) {
            buttonHtml = `
                <button class="py-2 px-5 border border-solid border-transparent text-white font-Wanted-Variable no-underline flex items-center justify-center gap-2.5 cursor-not-allowed text-[18px] rounded-[20px] bg-red-600" disabled>
                    Pending
                </button>`;
        } else {
            buttonHtml = `
                <button class="py-2 px-5 border border-solid border-transparent text-white font-Wanted-Variable no-underline flex items-center justify-center gap-2.5 cursor-pointer text-[18px] rounded-[20px] bg-gradient-to-r from-[#008d95bc] to-[#13c9d3] rounded-2xl hover:bg-green send-connect" data-username="${item.username}">
                    Connect
                </button>`;
        }

        return `
            <div class="grid grid-cols-2 hover:scale-95 transform transition duration-300 grid grid-cols-2 cursor-pointer">
                <a href="/profile/${item.username}/" class="flex flex-row gap-3 items-center">
                    <div class="flex flex-row gap-3 items-center">
                            <div class="flex justify-center items-center">
                                <img src="${item.profile_photo_url}" alt="${item.display_name}" class="lazyload size-11 rounded-full">
                            </div>
                        <div class="flex flex-col justify-center items-start gap-1">
                            <h2 class="font-Wanted-SemiBold text-Base">${item.display_name}</h2>
                            <p class="font-Wanted-Variable text-customGray5">@${item.username}</p>
                        </div>
                    </div>
                </a>
                <div class="flex justify-end items-center">
                    ${buttonHtml}
                </div>
            </div>`;
    }
});
