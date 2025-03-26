document.addEventListener("DOMContentLoaded", function () {
  try {
    const usernameElement = document.getElementById("socketUsername");
    if (!usernameElement) {
      console.error("socketUsername element not found");
      return;
    }
    
    const username = usernameElement.value;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socketUrl = `${protocol}//${window.location.host}/profile/${username}/`;
    
    console.log("Connecting profile WebSocket to:", socketUrl);
    
    let socket;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const reconnectDelay = 3000; // 3 seconds between reconnection attempts

    function connectWebSocket() {
      try {
        socket = new WebSocket(socketUrl);

        socket.onopen = function () {
          console.log("Profile WebSocket connection established");
          reconnectAttempts = 0; // Reset reconnect attempts when successfully connected
        };

        socket.onclose = function (event) {
          console.log("Profile WebSocket connection closed", event);
          
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
          console.error("Profile WebSocket error:", error);
        };

        socket.onmessage = function (event) {
          console.log("Profile WebSocket message received:", event.data);
          try {
            const data = JSON.parse(event.data);
            // Reload page to reflect friend status changes
            location.reload();
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
  } catch (error) {
    console.error("Error setting up WebSocket:", error);
  }
});
