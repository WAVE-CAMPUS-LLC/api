const username = document.getElementById("socketUsername").value;
const connectButton = document.getElementById("connectBtn");

if (username) console.log(username);
else console.log("No username found");

const socket = new WebSocket(
  `ws://${window.location.host}/profile/${username}/`
);

socket.onopen = function () {
  console.log("WebSocket connected for friend requests");
};

// socket.onmessage = function (event) {
//   const data = JSON.parse(event.data);
//   alert(data.message); // Show the response from the server
// };

connectButton.addEventListener("click", function () {
  sendFriendRequest();
});

function sendFriendRequest() {
  const message = { action: "send_friend_request" };
  socket.send(JSON.stringify(message));
  console.log(message);
  console.log("Friend request sent");
}

socket.onclose = function () {
  console.log("WebSocket disconnected for friend requests");
};
