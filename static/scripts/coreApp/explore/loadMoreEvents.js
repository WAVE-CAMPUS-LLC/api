let offset = 9;

function loadMoreEvents() {
    fetch(`/load-more/?offset=${offset}`)
        .then(response => response.json())
        .then(data => {
            const eventsContainer = document.getElementById('events-container');

            data.events.forEach(event => {
                if (event.status === "live") {
                    const eventCard = `
                        <a href="/event/${event.eventId}/" 
                           class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black" 
                           data-event-id="${event.eventId}" 
                           onclick="handleEventClick(event, '${event.eventId}')">
                            <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
                                <img src="${event.header_photo_url || '/static/images/explore/display.png'}" 
                                     alt="Event Header" 
                                     class="w-full h-[448px] rounded-2xl rounded-b-none object-cover">
                            </div>
                            <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
                                <h2 id="eventTitle" class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-2xl">
                                    ${event.title || 'Title not available'}
                                </h2>
                                <div class="eventSubInfo flex flex-col items-start gap-2 w-full font-Wanted-Variable text-customGray5">
                                    <p id="eventHost" class="flex flex-row justify-start">
                                        Hosted by @${event.host_username || 'Unknown host'}
                                    </p>
                                    <div class="flex flex-row justify-between w-full items-center">
                                        <p id="eventDate" class="w-full flex justify-start font-Wanted-Bold text-Medium">
                                            ${event.date || 'Date not available'}
                                        </p>
                                        <button class="favoriteEvent" type="button">
                                            ${event.is_favorite ? '<img src="/static/images/coreApp/eventDetails/favorite.svg" />' : ''}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </a>
                    `;
                    
                    // Insert the new event card into the container
                    eventsContainer.insertAdjacentHTML('beforeend', eventCard);
                }
            });

            // Increment offset for the next batch
            offset += 3;

            // Hide the "Load More" button if no more events are available
            if (!data.has_more) {
                document.getElementById('loadMoreButton').style.display = 'none';
            }
        })
        .catch(error => console.error('Error loading events:', error));
}
