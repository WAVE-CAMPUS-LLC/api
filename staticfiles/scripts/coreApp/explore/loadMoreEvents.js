// let offset = 7;

// function loadMoreEvents() {
//     fetch(`/load-more/?offset=${offset}`)
//         .then(response => response.json())
//         .then(data => {
//             const eventsContainer = document.getElementById('events-container');

//             data.events.forEach(event => {
//                 if (event.status === "live") {
//                     // Create a new event card
//                     const eventCard = document.createElement('a');
//                     eventCard.className = 'category-event-card';
//                     eventCard.href = `/event/${event.eventId}/`;
//                     eventCard.target = "_blank";

//                     // Create and append event image
//                     const imageDiv = document.createElement('div');
//                     imageDiv.className = 'category-image';
//                     const img = document.createElement('img');
//                     img.src = event.header_photo.url; // Ensure your view returns the full URL
//                     img.alt = "";
//                     imageDiv.appendChild(img);

//                     // Create and append event details
//                     const detailsDiv = document.createElement('div');
//                     detailsDiv.className = 'category-event-name';
//                     const title = document.createElement('h2');
//                     title.id = 'eventTitle';
//                     title.innerText = event.title;
//                     const subInfoDiv = document.createElement('div');
//                     subInfoDiv.className = 'eventSubInfo';
//                     const location = document.createElement('p');
//                     location.id = 'eventLocation';
//                     location.innerText = `Hosted by @${event.host__username}`;
//                     const date = document.createElement('p');
//                     date.id = 'eventDate';
//                     date.innerText = event.date;

//                     // Append sub-info elements to the details div
//                     subInfoDiv.appendChild(location);
//                     subInfoDiv.appendChild(date);
//                     detailsDiv.appendChild(title);
//                     detailsDiv.appendChild(subInfoDiv);

//                     // Append all parts to the event card
//                     eventCard.appendChild(imageDiv);
//                     eventCard.appendChild(detailsDiv);

//                     // Append the new event card to the events container
//                     eventsContainer.appendChild(eventCard);
//                 }
//             });

//             // Increment offset for the next batch
//             offset += 3;

//             // Hide the "Load More" button if no more events are available
//             if (!data.has_more) {
//                 document.getElementById('loadMoreButton').style.display = 'none';
//             }
//         })
//         .catch(error => console.error('Error loading events:', error));
// }

let offset = 7;

function loadMoreEvents() {
    fetch(`/load-more/?offset=${offset}`)
        .then(response => response.json())
        .then(data => {
            const eventsContainer = document.getElementById('events-container');

            data.events.forEach(event => {
                if (event.status === "live") {
                    // Create a new event card
                    const eventCard = document.createElement('a');
                    eventCard.className = 'category-event-card';
                    eventCard.href = `/event/${event.eventId}/`;
                    eventCard.target = "_blank";

                    // Create and append event image
                    const imageDiv = document.createElement('div');
                    imageDiv.className = 'category-image';
                    const img = document.createElement('img');
                    img.src = event.header_photo_url; // Use the correct field name
                    img.alt = "";
                    imageDiv.appendChild(img);

                    // Create and append event details
                    const detailsDiv = document.createElement('div');
                    detailsDiv.className = 'category-event-name';
                    const title = document.createElement('h2');
                    title.id = 'eventTitle';
                    title.innerText = event.title;
                    const subInfoDiv = document.createElement('div');
                    subInfoDiv.className = 'eventSubInfo';
                    const location = document.createElement('p');
                    location.id = 'eventLocation';
                    location.innerText = `Hosted by @${event.host_username}`; // Use the correct field name
                    const date = document.createElement('p');
                    date.id = 'eventDate';
                    date.innerText = event.date;

                    // Append sub-info elements to the details div
                    subInfoDiv.appendChild(location);
                    subInfoDiv.appendChild(date);
                    detailsDiv.appendChild(title);
                    detailsDiv.appendChild(subInfoDiv);

                    // Append all parts to the event card
                    eventCard.appendChild(imageDiv);
                    eventCard.appendChild(detailsDiv);

                    // Append the new event card to the events container
                    eventsContainer.appendChild(eventCard);
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
