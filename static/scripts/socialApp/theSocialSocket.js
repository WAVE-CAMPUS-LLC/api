let csrfToken;

document.addEventListener("DOMContentLoaded", function () {
  csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  const requestCountElement = document.getElementById("number-of-requests");
  const requestCountElementCrew = document.getElementById(
    "number-of-requests-crew"
  );

  let currentCount = parseInt(
    requestCountElement.getAttribute("data-initial-count")
  );
  let currentCountCrew = parseInt(
    requestCountElementCrew.getAttribute("data-initial-count")
  );

  requestCountElement.style.display = currentCount == 0 ? "none" : "block";
  requestCountElementCrew.style.display =
    currentCountCrew == 0 ? "none" : "block";

  const sharedEventsContainer = document.getElementById("shared-events");
  const sharedEventsIndicator = document.getElementById(
    "shared-events-indicator"
  );
  // on click function for the shared event
  sharedEventsContainer.addEventListener("click", (e) => {
    sharedEventsIndicator.style.display = "none";
  });

  const socket = new WebSocket(`ws://${window.location.host}/social/`);

  socket.onopen = function () {
    console.log("WebSocket connected for socialHomeView");
  };

  socket.onclose = function () {
    console.log("WebSocket closed for crew requests");

    // 1) Create the HTML for your overlay + popup
    const overlayHTML = `
      <div id="crew-updates-overlay" class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-[9999]">
        <div class="relative w-[400px] bg-white rounded-[10px] shadow-lg p-[20px] text-center">
          <button id="closeOverlayBtn" 
                  class="absolute top-[10px] right-[10px] text-2xl border-none bg-none cursor-pointer">
            &times;
          </button>
              <h4><strong>Live Updates are off!</strong></h4>
        </div>
      </div>
    `;

    // 2) Insert this HTML into the DOM
    document.body.insertAdjacentHTML("beforeend", overlayHTML);

    // 3) Attach close functionality to the button
    document.getElementById("closeOverlayBtn").onclick = function () {
      document.getElementById("crew-updates-overlay").remove();
    };
  };

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    switch (data.action) {
      case "send":
        currentCount += 1;
        requestCountElement.style.display = "block";

        if (currentCount > 9) {
          requestCountElement.textContent = "9+";
        } else {
          requestCountElement.textContent = currentCount;
        }
        renderFriendRequest(data.friend_request);
        break;

      case "cancel":
        currentCount -= 1;
        if (currentCount <= 0) {
          requestCountElement.style.display = "none";
        } else {
          requestCountElement.style.display = "block";
          requestCountElement.textContent = currentCount;
        }
        removeFriendRequest(data.friend_request, currentCount);
        break;

      case "remove":
        location.reload();
        break;

      case "sendCrew":
        currentCountCrew += 1;
        requestCountElementCrew.style.display = "block";

        if (currentCountCrew > 9) {
          requestCountElementCrew.textContent = "9+";
        } else {
          requestCountElementCrew.textContent = currentCountCrew;
        }
        renderCrewRequest(data.crew_request, currentCountCrew);
        break;

      case "kickCrew":
        currentCountCrew -= 1;
        if (currentCountCrew <= 0) {
          requestCountElementCrew.style.display = "none";
        } else {
          requestCountElementCrew.style.display = "block";
          requestCountElementCrew.textContent = currentCountCrew;
        }
        removeCrew(data.crew_request, currentCountCrew);
        break;

      case "declineCrewRequest":
      case "acceptCrewRequest":
        location.reload();
        break;

      case "shared_event":
        console.log("Shared event received");
        console.log("Shared event received");
        console.log("Shared event received");
        const sharedTab = document.querySelector(
          '.social-tab[data-tab="shared"]'
        );
        const isSharedTabActive = sharedTab.classList.contains("tab-active");
        if (!isSharedTabActive) {
          sharedEventsIndicator.style.display = "block";
        }
        renderSharedEvent(data.shared_event);
        break;

      default:
        console.error("Unknown action:", data.action);
        break;
    }
  };
});

function renderFriendRequest(request) {
  const emptyContainer = document.getElementById("empty-friend-requests");
  let friendRequestsContainer;
  if (emptyContainer) {
    emptyContainer.remove();
    friendRequestsContainer = document.getElementById("incomingFriendRequests");
  } else {
    friendRequestsContainer = document.getElementById("friend-request-div");
  }

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
                <button class="accept bg-[red] flex justify-center font-Wanted-Bold text-white rounded-xl py-2 px-4" type="submit" role="button">
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
  const friendRequest = document.getElementById(request.requestId);
  if (friendRequest) {
    friendRequest.remove();
  }

  if (currentCount <= 0) {
    const friendRequestsContainer =
      document.getElementById("friend-request-div");
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
  const emptyContainer = document.getElementById("empty-crew-invitations");
  const crewRequestsContainer = document.getElementById("receivedCrewInvites");
  emptyContainer?.remove();

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
          <button class="accept bg-[red] flex justify-center font-Wanted-Bold text-white rounded-xl py-2 px-4" type="submit" name="action" value="joinCrew" role="button">
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
  const crewView = document.getElementById(request.crewId);
  console.log(request.crewId);
  crewView.remove();
  if (currentCount <= 0) {
    const crewRequestsContainer = document.getElementById("crewsImIn");
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
  const emptyContainer = document.getElementById("empty-shared-events");
  const sharedEventsContainer = document.getElementById("sharedEventsWithMe");
  emptyContainer?.remove();

  const sharedEventHTML = `
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

  sharedEventsContainer.insertAdjacentHTML("beforeend", sharedEventHTML);
};
