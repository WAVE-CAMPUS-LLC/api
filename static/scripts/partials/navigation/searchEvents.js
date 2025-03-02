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

    let is_processing = false; //debouncing
    $(document).on('click', '.pageChange', (event)=> {
        const context = $('.search-input').data('context');
        const idName = $('.search-input').data('id');
        if(is_processing) {return;}
        is_processing = true;
        event.preventDefault();


        const button = event.currentTarget;
        const page = button.value;
        $('.pageChange').removeClass('active_page_btn');
        $(button).addClass('active_page_btn')
        console.log(page + 'This is the page yo')
        perform_page_change(context, idName, page-1);

        is_processing = false;
    });

    function perform_page_change(context, idName, page) {
        const $input = $(`.search-input[data-context=${context}][data-id=${idName}]`);
        const query = $input.val().trim();

        if (query.length > 0) {
            const $results = $(`.${context}-search-results-${idName}`);
            $results.removeClass('hidden').fadeIn(300);
            showLoadingNotice(context, idName);

            // AJAX call for search
            const searchUrl = document.getElementById('searchUrl').value;
            $.ajax({
                url: searchUrl,
                data: { query, context },
                dataType: 'json',
                success: function (data) {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.empty();
                    $items.html(``);

                    if (data.results && data.results.length > page*6) {
                        i = page*6;
                        while (i < data.results.length && i < page*6+6) {
                            const resultHtml = context === 'event'
                                ? renderEventItem(data.results[i])
                                : renderFriendItem(data.results[i]);
                            $items.append(resultHtml); 
                            i++;
                        }
                    }
                     else {
                        $items.html(`
                            <div class="flex justify-center py-5">
                                <h3 class="font-Wanted-ExtraBold text-[40px] text-center">No results found</h3>
                            </div>
                        `);
                    }
                },
                error: function () {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.html('<p class="error-message">Failed to fetch results. Please try again.</p>');
                }
            });
        }
    }


    function performSearch(context, idName) {
        const $input = $(`.search-input[data-context=${context}][data-id=${idName}]`);
        const query = $input.val().trim();

        if (query.length > 0) {
            const $results = $(`.${context}-search-results-${idName}`);
            $results.removeClass('hidden').fadeIn(300);
            showLoadingNotice(context, idName);

            // AJAX call for search
            const searchUrl = document.getElementById('searchUrl').value;
            $.ajax({
                url: searchUrl,
                data: { query, context },
                dataType: 'json',
                success: function (data) {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.empty();

                    // console.log(data.results.length + 'this is THE LENGTH');
                    pages = parseInt(data.results.length/6);
                    const $page_num = $(`.${context}-search-pages-${idName}`);
                    $page_num.empty();
                    page_count = 1
                    while (page_count <= pages+1) {
                        count_result = renderCount(page_count);
                        $page_num.append(count_result);
                        page_count++;
                    }


                    if (data.results && data.results.length > 0 && data.results.length<=6) {
                        data.results.forEach(item => {
                            const resultHtml = context === 'event'
                                ? renderEventItem(item)
                                : renderFriendItem(item);
                            $items.append(resultHtml); 
                        })
                    }
                    else if (data.results && data.results.length > 0) {
                        for(i = 0; i < 6; i++) {
                            const resultHtml = context === 'event'
                                ? renderEventItem(data.results[i])
                                : renderFriendItem(data.results[i]);
                            $items.append(resultHtml); 
                        }
                    }
                     else {
                        $items.html(`
                            <div class="flex justify-center py-5">
                                <h3 class="font-Wanted-ExtraBold text-[40px] text-center">No results found</h3>
                            </div>
                        `);
                    }
                },
                error: function () {
                    const $items = $(`.${context}-search-items-${idName}`);
                    $items.html('<p class="error-message">Failed to fetch results. Please try again.</p>');
                }
            });
        }
    }


    // function sendConnectRequest(button) {
    //     const username = button.dataset.username;

    //     $.ajax({
    //         url: '/send-connect-request/',  // You'll need to create this endpoint
    //         method: 'POST',
    //         data: {
    //             'action': 'send_request',
    //             'socketUsername': username,
    //             'csrfmiddlewaretoken': document.querySelector('[name=csrfmiddlewaretoken]').value
    //         },
    //         success: function (response) {
    //             if (response.status === 'success') {
    //                 // Update button state
    //                 button.textContent = 'Pending';
    //                 button.classList.add('pending');
    //                 // You might want to disable the button or change its appearance
    //             }
    //         },
    //         error: function (xhr, status, error) {
    //             console.error('Error sending connect request:', error);
    //         }
    //     });
    // }

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

    // $(document).on('click', '.send-connect', function () {
    //     sendConnectRequest(this);
    // });

    function renderCount(count) {
        return  `<div class="border border-green rounded-2xl flex items-center">
                    <button type="button" class="pageChange w-full p-3 border rounded-2xl border-black bg-black text-white font-Wanted-Medium text-Semi-Medium cursor-pointer" value="${count}">
                        <span>${count}</span>
                    </button>
                </div>`;
    }

    function renderFriendItem(item) {
        let buttonHtml = '';
        if (item.is_friend) {
            // Do not display the Connect button if already friends
            buttonHtml = `
                <button class="bg-[#00b500] text-white py-2 px-5 border border-solid border-transparent pending cursor-not-allowed  text-[18px] rounded-[20px]" type="button" disabled>
                    Friend
                </button>`;
        } else if (item.has_sent_friend_request) {
            // Display a disabled button with "Pending" text if request is sent
            buttonHtml = `
                <button class="bg-red-600 text-white py-2 px-5 border border-solid border-transparent pending cursor-not-allowed  text-[18px] rounded-[20px]" type="button" disabled>
                    Pending
                </button>`;
        } else {
            // Display the active "Connect" button if no request is sent and not friends
            buttonHtml = `
                <button class="py-2 px-5 border border-solid border-transparent text-white font-Wanted-Variable no-underline flex items-center justify-center gap-2.5 cursor-pointer text-[18px] rounded-[20px] bg-gradient-to-r from-[#008d95bc] to-[#13c9d3] rounded-2xl hover:bg-green send-connect" type="button" role="button" data-username="${item.username}">
                    Connect
                </button>`;
        }

        return `
            <div class="grid grid-cols-2 hover:scale-95 transform transition duration-300 grid grid-cols-2 cursor-pointer">
                <div class="flex flex-row gap-3 items-center">
                    <div class="flex justify-center items-center">
                        <img src="${item.profile_photo_url}" alt="${item.display_name}" class="lazyload size-11 rounded-full">
                    </div>
                    <div class="flex flex-col justify-center items-start gap-1">
                        <h2 class="font-Wanted-SemiBold text-Base">${item.display_name}</h2>
                        <p class="font-Wanted-Variable text-customGray5">@${item.username}</p>
                    </div>
                </div>
                <div class="flex justify-end items-center">
                    ${buttonHtml}
                </div>
            </div>`;
    }
});
