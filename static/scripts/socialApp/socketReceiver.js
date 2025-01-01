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
      removeCrew(data.crew_request, currentCountCrew);
    }
  };

  socket.onclose = function () {
    console.log("WebSocket disconnected for socialHomeView");
  };
});

function renderFriendRequest(request) {
  const emptyContainer = document.getElementById("empty-friend-requests");
  let friendRequestsContainer;
  if (emptyContainer) {
    emptyContainer.remove();
    friendRequestsContainer = document.getElementById("friend-requests");
  } else {
    friendRequestsContainer = document.getElementById(
      "friend-requests-container"
    );
  }

  const friendRequestHTML = `
  <div class="request-home-body" id="friend-requests-container">
    <div class="request-item" id="${request.requestId}">
      <div class="request-left">
        <div class="request-pfp">
          <img src="/static/images/socialApp/publicProfile/profile/E.L.png" alt="Profile Picture" />
        </div>
        <div class="request-names">
          <h1>${request.sender_first_name} ${request.sender_last_name}</h1>
          <p>Sent at ${new Date(request.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
        </div>
      </div>
      <div class="request-actions">
        <form method="POST">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
          <input type="hidden" name="friend_request_id" value="${request.requestId}">
          <input type="hidden" name="action" value="acceptRequest">
          <button class="accept" type="submit" role="button">
            <img src="/static/images/socialApp/socialHome/accept.svg" alt="Accept Friend Request">
          </button>
        </form>
        <form method="POST">
          <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
          <input type="hidden" name="friend_request_id" value="${request.requestId}">
          <input type="hidden" name="action" value="declineRequest">
          <button class="decline" type="submit" role="button">
            <img src="/static/images/socialApp/socialHome/decline.svg" alt="Decline Friend Request">
          </button>
        </form>
      </div>
    </div>
  </div>
  `;

  friendRequestsContainer.insertAdjacentHTML("beforeend", friendRequestHTML);
}

function removeFriendRequest(request, currentCount) {
  const friendRequest = document.getElementById(request.requestId);
  friendRequest.remove();

  if (currentCount <= 0) {
    const friendRequestsContainer = document.getElementById(
      "friend-requests-container"
    );
    const emptyFriendRequestsHTML = `
    <div class="emptyContainer" id="empty-friend-requests">
      <div>
        <img src="/static/images/collegeManagementApp/collegeInformation/empty-listing.svg" />
      </div>
      <div>
        <p>
          Currently, no friend requests.
        </p>
      </div>
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
  const crewRequestsContainer = document.getElementById(
    "crew-invitations-container"
  );
  emptyContainer?.remove();

  const crewRequestHTML = `
    <div class="crew-invite-item" id="${request.crewId}">
        <div class="cit-left">
            <div class="cit-pfp">
                <img src="/static/images/socialApp/publicProfile/profile/E.L.png" alt="Profile Picture" />
            </div>
            <div class="cit-name">
                <h5><span class="crew-name">${request.crew}</span> has invited you!</h5>
                <p>Invited by <a href="{% url "social:publicProfile" username=${request.sender.username} %}" target="_blank">
                    @${request.sender.username}</a>
                </p>
            </div>
        </div>
        <div class="cit-right">
            <form method="POST">
                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                <input type="hidden" name="crew_id" value="${request.crewId}" />
                <button class="accept" type="submit" name="action" value="joinCrew" role="button">
                    <img src="/static/images/socialApp/socialHome/accept.svg" alt="Accept Friend Request" />
                </button>
                <button class="decline" type="submit" name="action" value="declineCrew" role="button">
                    <img src="/static/images/socialApp/socialHome/decline.svg" alt="Decline Friend Request" />
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
  crewView.remove();
  currentCount -= 1;
  if (currentCount <= 0) {
    const crewRequestsContainer = document.getElementById("crews-body");
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
