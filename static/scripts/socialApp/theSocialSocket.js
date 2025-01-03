let csrfToken;
document.addEventListener("DOMContentLoaded", function () {
  csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");
  const requestCountElement = document.getElementById("number-of-requests");

  let currentCount = parseInt(
    requestCountElement.getAttribute("data-initial-count")
  );

  if (currentCount == 0) {
    requestCountElement.style.display = "none";
  } else {
    requestCountElement.style.display = "block";
  }

  const requestCountElementCrew = document.getElementById(
    "number-of-requests-crew"
  );

  let currentCountCrew = parseInt(
    requestCountElementCrew.getAttribute("data-initial-count")
  );

  if (currentCountCrew == 0) {
    requestCountElementCrew.style.display = "none";
  } else {
    requestCountElementCrew.style.display = "block";
  }

  const socket = new WebSocket(`ws://${window.location.host}/social/`);

  socket.onopen = function () {
    console.log("WebSocket connected for socialHomeView");
  };

  socket.onclose = function () {
    console.log("WebSocket closed for crew requests");

    // Create the overlay
    const overlay = document.createElement("div");
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    overlay.style.display = "flex";
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.zIndex = "9999";

    // Create the pop-up container
    const popup = document.createElement("div");
    popup.style.position = "relative";
    popup.style.width = "400px";
    popup.style.backgroundColor = "#fff";
    popup.style.borderRadius = "10px";
    popup.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.2)";
    popup.style.padding = "20px";
    popup.style.textAlign = "center";

    // Create the close button
    const closeButton = document.createElement("button");
    closeButton.innerHTML = "&times;";
    closeButton.style.position = "absolute";
    closeButton.style.top = "10px";
    closeButton.style.right = "10px";
    closeButton.style.border = "none";
    closeButton.style.background = "none";
    closeButton.style.fontSize = "20px";
    closeButton.style.cursor = "pointer";

    // Add close functionality
    closeButton.onclick = function () {
      document.body.removeChild(overlay);
    };

    // Add content to the pop-up
    popup.innerHTML = `
      <h4><strong>Live Updates are off!</strong></h4>
    `;
    popup.appendChild(closeButton);

    // Add pop-up to the overlay
    overlay.appendChild(popup);

    // Append the overlay to the body
    document.body.appendChild(overlay);
  };

  socket.onmessage = function (event) {
    const data = JSON.parse(event.data);

    if (data.action == "send") {
      currentCount += 1;
      requestCountElement.style.display = "block";

      if (currentCount > 9) {
        requestCountElement.textContent = "9+";
      } else {
        requestCountElement.textContent = currentCount;
      }
      renderFriendRequest(data.friend_request);
    } else if (data.action == "cancel") {
      currentCount -= 1;
      if (currentCount <= 0) {
        requestCountElement.style.display = "none";
      } else {
        requestCountElement.style.display = "block";
        requestCountElement.textContent = currentCount;
      }
      removeFriendRequest(data.friend_request, currentCount);
    } else if (data.action == "remove") {
      location.reload();
    } else if (data.action == "sendCrew") {
      currentCountCrew += 1;
      requestCountElementCrew.style.display = "block";

      if (currentCountCrew > 9) {
        requestCountElementCrew.textContent = "9+";
      } else {
        requestCountElementCrew.textContent = currentCountCrew;
      }
      renderCrewRequest(data.crew_request, currentCountCrew);
    } else if (data.action == "kickCrew") {
      currentCountCrew -= 1;
      if (currentCountCrew <= 0) {
        requestCountElementCrew.style.display = "none";
      } else {
        requestCountElementCrew.style.display = "block";
        requestCountElementCrew.textContent = currentCountCrew;
      }
      removeCrew(data.crew_request, currentCountCrew);
    } else if (
      data.action == "declineCrewRequest" ||
      data.action == "acceptCrewRequest"
    ) {
      location.reload();
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
