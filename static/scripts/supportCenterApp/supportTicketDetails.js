// document.addEventListener('DOMContentLoaded', function () {
//     const roomName = "{{ ticket.ticket_id }}";
//     const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
//     const chatSocket = new WebSocket(
//         protocol + window.location.host + '/ws/chat/' + roomName + '/'
//     );

//     chatSocket.onmessage = function (e) {
//         const data = JSON.parse(e.data);
//         // Update the messages on the page
//         fetchMessages();
//     };

//     chatSocket.onclose = function (e) {
//         console.error('Chat socket closed unexpectedly', e.code, e.reason);
//     };

//     function fetchMessages() {
//         fetch('{% url "support:ticket_messages" ticket.ticket_id %}')
//             .then(response => response.text())
//             .then(html => {
//                 document.getElementById('messages').innerHTML = html;
//             })
//             .catch(error => console.error("Error fetching messages:", error));
//     }
// });