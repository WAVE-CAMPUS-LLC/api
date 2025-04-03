let csrfToken;

document.addEventListener("DOMContentLoaded", function () {
  csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  const requestCountElement = document.getElementById("number-of-requests");
  const requestCountElementCrew = document.getElementById(
    "number-of-requests-crew"
  );
  const goWithRequestsIndicator = document.getElementById(
    "go-with-requests-indicator"
  );

  // Default to 0 if elements don't exist or don't have the attribute
  let currentCount = requestCountElement ? parseInt(
    requestCountElement.getAttribute("data-initial-count") || "0"
  ) : 0;
  
  let currentCountCrew = requestCountElementCrew ? parseInt(
    requestCountElementCrew.getAttribute("data-initial-count") || "0"
  ) : 0;
  
  let goWithRequestsCount = 0;

  if (requestCountElement) {
    requestCountElement.style.display = currentCount == 0 ? "none" : "block";
  }
  
  if (requestCountElementCrew) {
    requestCountElementCrew.style.display =
      currentCountCrew == 0 ? "none" : "block";
  }
  
  if (goWithRequestsIndicator) {
    goWithRequestsIndicator.style.display = "none";
  }

  const sharedEventsContainer = document.getElementById("shared-events");
  const sharedEventsIndicator = document.getElementById(
    "shared-events-indicator"
  );
  
  // on click function for the shared event
  if (sharedEventsContainer && sharedEventsIndicator) {
    sharedEventsContainer.addEventListener("click", (e) => {
      sharedEventsIndicator.style.display = "none";
    });
  }

  // Use secure WebSocket connection if the page is loaded over HTTPS
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socketUrl = `${protocol}//${window.location.host}/social/`;
  console.log("Connecting to WebSocket at:", socketUrl);
  
  let socket;
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000; // 3 seconds between reconnection attempts

  function connectWebSocket() {
    try {
      socket = new WebSocket(socketUrl);

      socket.onopen = function () {
        console.log("WebSocket connection established");
        reconnectAttempts = 0; // Reset reconnect attempts when successfully connected
      };

      socket.onclose = function (event) {
        console.log("WebSocket connection closed", event);
        
        // Try to reconnect if not closed normally and we haven't exceeded max attempts
        if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
          setTimeout(connectWebSocket, reconnectDelay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          console.log("Maximum reconnection attempts reached");
        }
      };

      socket.onerror = function (error) {
        console.error("WebSocket error:", error);
      };

      socket.onmessage = function (event) {
        console.log("WebSocket message received:", event.data);
        try {
          const data = JSON.parse(event.data);

          switch (data.action) {
            case "send":
              currentCount += 1;
              if (requestCountElement) {
                requestCountElement.style.display = "block";
                if (currentCount > 9) {
                  requestCountElement.textContent = "9+";
                } else {
                  requestCountElement.textContent = currentCount;
                }
                renderFriendRequest(data.friend_request);
              }
              break;

            case "cancel":
              currentCount -= 1;
              if (requestCountElement) {
                if (currentCount <= 0) {
                  requestCountElement.style.display = "none";
                } else {
                  requestCountElement.style.display = "block";
                  requestCountElement.textContent = currentCount;
                }
                removeFriendRequest(data.friend_request, currentCount);
              }
              break;

            case "remove":
              location.reload();
              break;

            case "sendCrew":
              currentCountCrew += 1;
              if (requestCountElementCrew) {
                requestCountElementCrew.style.display = "block";
                if (currentCountCrew > 9) {
                  requestCountElementCrew.textContent = "9+";
                } else {
                  requestCountElementCrew.textContent = currentCountCrew;
                }
                renderCrewRequest(data.crew_request, currentCountCrew);
              }
              break;

            case "kickCrew":
              currentCountCrew -= 1;
              if (requestCountElementCrew) {
                if (currentCountCrew <= 0) {
                  requestCountElementCrew.style.display = "none";
                } else {
                  requestCountElementCrew.style.display = "block";
                  requestCountElementCrew.textContent = currentCountCrew;
                }
                removeCrew(data.crew_request, currentCountCrew);
              }
              break;

            case "declineCrewRequest":
            case "acceptCrewRequest":
              // Only reload if we're on the crew page
              if (window.location.pathname.includes('/crew/')) {
                location.reload();
              }
              break;

            case "sendGoWith":
              goWithRequestsCount += 1;
              if (goWithRequestsIndicator) {
                goWithRequestsIndicator.style.display = "block";
              }
              // Show go-with request in real-time if we're on the social home page
              renderGoWithRequest(data.go_with_request);
              break;
              
            case "acceptGoWithRequest":
            case "declineGoWithRequest":
            case "cancelGoWithRequest":
              // Update go-with request UI without page refresh
              updateGoWithRequestStatus(data.go_with_request);
              break;

            case "shared_event":
              if (sharedEventsIndicator) {
                const sharedTab = document.querySelector(
                  '.social-tab[data-tab="shared"]'
                );
                const isSharedTabActive = sharedTab && 
                  sharedTab.classList.contains("social-tab-active");
                if (!isSharedTabActive) {
                  sharedEventsIndicator.style.display = "block";
                }
                renderSharedEvent(data.shared_event);
              }
              break;

            default:
              console.log("Unknown action:", data.action);
              break;
          }
        } catch (error) {
          console.error("Error processing WebSocket message:", error);
        }
      };
    } catch (error) {
      console.error("Error connecting to WebSocket:", error);
    }
  }

  // Start the WebSocket connection
  connectWebSocket();
});

function renderFriendRequest(request) {
  if (!request) return;
  
  const emptyContainer = document.getElementById("empty-friend-requests");
  let friendRequestsContainer;
  if (emptyContainer) {
    emptyContainer.remove();
    friendRequestsContainer = document.getElementById("incomingFriendRequests");
  } else {
    friendRequestsContainer = document.getElementById("friend-request-div");
  }

  if (!friendRequestsContainer) return;

  const friendRequestHTML = `
    <div class="flex flex-col gap-4 items-center cursor-pointer border border-custom-rgba8 hover:border-green shadow-custom-shadow-3 rounded-2xl p-5" id="${request.requestId}">
        <div class="request-left">
            <div class="w-full flex justify-center">
                <img src="${request.profile_picture}" alt="Profile Picture" class="rounded-full size-14" />
            </div>
            <div class="user-names flex flex-col gap-1 justify-center items-center">
                <h1 class="userFullname font-Wanted-Bold text-Large text-center">${request.sender_first_name} ${request.sender_last_name}</h1>
                <p class="font-Wanted-Variable text-Medium text-customGray5 text-center">Sent at ${new Date(request.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
            </div>
        </div>
        <div class="request-actions w-full flex flex-row gap-2 justify-between items-center">
            <form method="POST" class="w-full flex justify-start">
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <input type="hidden" name="friend_request_id" value="${request.requestId}">
                <input type="hidden" name="action" value="acceptRequest">  
                <button class="accept bg-[#0f960f] flex justify-center font-Wanted-Bold text-white rounded-xl py-2 px-4" type="submit" role="button">
                    Accept
                </button>
            </form>
            <form method="POST" class="w-full flex justify-end">
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <input type="hidden" name="friend_request_id" value="${request.requestId}">
                <input type="hidden" name="action" value="declineRequest"> 
                <button class="decline flex justify-center font-Wanted-Bold text-white bg-[red] rounded-xl py-2 px-4" type="submit" role="button">
                    Reject
                </button>
            </form>
        </div>
    </div>
  `;

  friendRequestsContainer.insertAdjacentHTML("beforeend", friendRequestHTML);
}

function removeFriendRequest(request, currentCount) {
  if (!request) return;
  
  const friendRequest = document.getElementById(request.requestId);
  if (friendRequest) {
    friendRequest.remove();
  }

  if (currentCount <= 0) {
    const friendRequestsContainer =
      document.getElementById("friend-request-div");
      
    if (!friendRequestsContainer) return;
    
    const emptyFriendRequestsHTML = `
      <div id="empty-friend-requests" class="emptyContainer h-full w-full rounded-[20px] py-[70px] flex justify-center flex-col gap-[10px] items-center bg-[rgba(146,146,146,0.096)]">
          <div>
              <img class="w-[30px] after-xsm:w-[40px] sm:w-[50px] md:w-[60px]" src="/static/images/coreApp/eventDetails/friends.svg" alt="No Friends Icon" />
          </div>
          <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-black text-center">No received friend requests. Invite your friends!</p>
      </div>
    `;

    friendRequestsContainer.insertAdjacentHTML(
      "beforeend",
      emptyFriendRequestsHTML
    );
  }
}

const renderCrewRequest = (request, currentCount) => {
  if (!request) return;
  
  const emptyContainer = document.getElementById("empty-crew-invitations");
  const crewRequestsContainer = document.getElementById("receivedCrewInvites");
  
  if (!crewRequestsContainer) return;
  
  if (emptyContainer) {
    emptyContainer.remove();
  }

  const crewRequestHTML = `
    <div class="flex flex-col gap-3 items-center cursor-pointer border border-custom-rgba8 hover:border-green shadow-custom-shadow-3 rounded-2xl p-5" id="${request.crewId}">
      <div class="flex flex-col gap-2 items-center">
        <div class="cit-name text-center flex flex-col justify-center items-center">
          <h5 class="font-Wanted-SemiBold text-Medium">${request.crew} has invited you!</h5>
          <p class="font-Wanted-Variable text-XSmall text-center text-customGray5">
            Invited by 
            <a href="/social/publicProfile/${request.sender.username}" target="_blank">
              @${request.sender.username}
            </a>
          </p>
        </div>
      </div>
      <div class="cit-right">
        <form method="POST" class="flex flex-row gap-2 justify-between">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
          <input type="hidden" name="crew_id" value="${request.crewId}" />
          <button class="accept bg-[#0f960f] flex justify-center font-Wanted-Bold text-white rounded-xl py-2 px-4" type="submit" name="action" value="joinCrew" role="button">
            Join
          </button>
          <button class="decline flex justify-center font-Wanted-Bold text-white bg-[red] rounded-xl py-2 px-4" type="submit" name="action" value="declineCrew" role="button">
            Decline
          </button>
        </form>
      </div>
    </div>
  `;

  crewRequestsContainer.innerHTML =
    currentCount <= 0 ? "" : crewRequestsContainer.innerHTML;
  crewRequestsContainer.insertAdjacentHTML("beforeend", crewRequestHTML);
};

const removeCrew = (request, currentCount) => {
  if (!request) return;
  
  const crewView = document.getElementById(request.crewId);
  if (!crewView) return;
  
  crewView.remove();
  
  if (currentCount <= 0) {
    const crewRequestsContainer = document.getElementById("crewsImIn");
    if (!crewRequestsContainer) return;
    
    const emptyCrewRequestsHTML = `
        <div class="emptyContainer" id="emptyCrewView">
        <div>
            <img src="/static/images/collegeManagementApp/collegeInformation/empty-listing.svg"/>
        </div>
        <div>
            <p>
                Create a crew and invite your friends!
            </p>
        </div>
    </div>
  `;
    crewRequestsContainer.insertAdjacentHTML(
      "beforeend",
      emptyCrewRequestsHTML
    );
  }
};

const renderSharedEvent = (request) => {
  if (!request) return;
  
  const emptyContainer = document.getElementById("empty-shared-events");
  if (emptyContainer) {
    emptyContainer.remove();
  }

  let sharedEventHTML;
  let sharedEventsContainer = document.getElementById("sharedEventsWithMe");

  if (sharedEventsContainer) {
    sharedEventHTML = `
    <a target="_blank" href="/event/${request.event_id}/" class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
        <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
            <img src="${request.header_photo}" alt="" class="w-full h-[200px] rounded-2xl rounded-b-none object-cover">
        </div>
        <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
            <h2 id="eventTitle" class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-xl">${request.event}</h2>
            <div class="eventSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                <p id="eventHost" class="flex flex-row justify-start">Shared by @${request.sender.username}</p>
                <p id="eventDate" class="w-full flex justify-end font-Wanted-Bold text-Large">${request.date}</p>
            </div>
        </div>
    </a>
  `;
  } else {
    sharedEventsContainer = document.getElementById("sharedWithMe");
    if (!sharedEventsContainer) return;
    
    sharedEventHTML = `
    <div id="sharedEventsWithMe" class="grid grid-cols-1 xxsm:grid-cols-2 md:grid-cols-3 3xl:grid-cols-4 gap-5">
      <a target="_blank" href="/event/${request.event_id}/" class="category-event-card hover:category-image hover:scale-95 transform transition duration-300 flex flex-col justify-center items-center cursor-pointer overflow-hidden p-[10px] text-black">
          <div class="category-image w-full rounded-2xl shadow-custom-shadow-3">
              <img src="${request.header_photo}" alt="" class="w-full h-[200px] rounded-2xl rounded-b-none object-cover">
          </div>
          <div class="category-event-name font-Wanted-SemiBold text-Base flex flex-col justify-center items-start gap-1 w-full border border-custom-rgba5 rounded-bl-2xl rounded-br-2xl shadow-custom-shadow-3 border-t-2 px-5 p-2">
              <h2 id="eventTitle" class="whitespace-nowrap overflow-hidden text-ellipsis w-full text-left text-xl">${request.event}</h2>
              <div class="eventSubInfo flex flex-col items-start gap-[1px] w-full font-Wanted-Variable text-customGray5">
                  <p id="eventHost" class="flex flex-row justify-start">Shared by @${request.sender.username}</p>
                  <p id="eventDate" class="w-full flex justify-end font-Wanted-Bold text-Large">${request.date}</p>
              </div>
          </div>
      </a>
    </div>
    `;
  }

  sharedEventsContainer.insertAdjacentHTML("beforeend", sharedEventHTML);
};

// New function to render go-with requests in real-time
const renderGoWithRequest = (request) => {
  if (!request) return;
  
  // Get go-with container on the social home page
  const goWithContainer = document.getElementById("incomingGoWithRequests");
  if (!goWithContainer) return;
  
  const emptyContainer = goWithContainer.querySelector(".emptyContainer");
  if (emptyContainer) {
    emptyContainer.remove();
  }
  
  const goWithRequestHTML = `
    <div class="flex flex-col gap-4 items-center cursor-pointer border border-custom-rgba8 hover:border-green shadow-custom-shadow-3 rounded-2xl p-5" id="go-with-${request.requestId}">
      <a target="_blank" href="/social/publicProfile/${request.sender.username}" id="${request.sender.username}">
        <div class="user-pfp w-full flex justify-center">
          <img src="${request.sender.profile_photo}" alt="Profile Picture" class="rounded-full size-14" />
        </div>
      </a>
      <div class="user-names flex flex-col gap-1 items-center">
        <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-black text-center">
          ${request.sender.first_name} ${request.sender.last_name} wants to go with you to "${request.event.title}"
        </p>
        <div class="flex flex-row justify-center items-center gap-4">
          <form method="POST" class="flex justify-center items-center gap-4">
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
            <input type="hidden" name="go_with_request_id" value="${request.requestId}">
            <input type="hidden" name="action" value="acceptGoWithRequest"> 
            <button class="accept flex justify-center font-Wanted-Bold text-white bg-[green] rounded-xl py-2 px-4" type="submit" role="button">
              &#10004;
            </button>
          </form>
          <form method="POST" class="flex justify-center items-center gap-4">
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
            <input type="hidden" name="go_with_request_id" value="${request.requestId}">
            <input type="hidden" name="action" value="declineGoWithRequest"> 
            <button class="decline flex justify-center font-Wanted-Bold text-white bg-[red] rounded-xl py-2 px-4" type="submit" role="button">
              &#10007;
            </button>
          </form>
        </div>
      </div> 
    </div>
  `;
  
  goWithContainer.insertAdjacentHTML("beforeend", goWithRequestHTML);
};

// Update go-with request status without page refresh
const updateGoWithRequestStatus = (request) => {
  if (!request) return;
  
  const requestElement = document.getElementById(`go-with-${request.requestId}`);
  if (!requestElement) return;
  
  if (request.status === "accepted" || request.status === "Accepted") {
    // Update UI to show accepted status
    requestElement.querySelector(".user-names").innerHTML = `
      <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-black text-center">
        Going with ${request.receiver.first_name} ${request.receiver.last_name} to "${request.event.title}"
      </p>
      <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-green text-center">
        Accepted
      </p>
    `;
  } else if (request.status === "declined" || request.status === "Declined") {
    // Update UI to show declined status
    requestElement.querySelector(".user-names").innerHTML = `
      <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-black text-center">
        Request to go with ${request.receiver.first_name} ${request.receiver.last_name} to "${request.event.title}"
      </p>
      <p class="font-Wanted-Variable text-[10px] after-xsm:text-[12px] sm:text-[14px] md:text-[16.5px] text-[red] text-center">
        Declined
      </p>
    `;
  } else if (request.status === "cancelled" || request.status === "Cancelled") {
    // Remove the go-with request from the UI
    requestElement.remove();
  }
};
