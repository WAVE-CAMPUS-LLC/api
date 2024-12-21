from channels.generic.websocket import AsyncWebsocketConsumer
import json

class FriendRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract the target username from the URL
        self.target_user = self.scope["url_route"]["kwargs"]["username"]
        # self.group_name = f"user_{self.scope['user'].id}"
        # await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
    # If you ever use socket.send() from the frontend, this is where you will receive the message - currently not used
    # async def receive(self, text_data):
        
        # # Parse the incoming WebSocket message
        # data = json.loads(text_data)
        # sender = self.scope["user"]  # Current logged-in user

        # # Logic to send a friend request
        #     # Save the friend request (pseudo-code)
        #     # FriendRequest.objects.create(sender=sender, receiver=self.target_user)

        #     # Notify the target user in the SocialHomeConsumer WebSocket group
        # channel_layer = self.channel_layer
        # await channel_layer.group_send(
        #     f"user_{self.target_user}",
        #     {
        #         "type": "friend_request_update",
        #         "data": {
        #             "message": f"{sender.username} sent you a friend request!",
        #         },
        #     },
        # )

    async def disconnect(self, close_code):
        pass

class SocialHomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Authenticate the user and create a group based on the user ID
        self.group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def friend_request_update(self, event):
        # Send the friend request update to the client
        await self.send(text_data=json.dumps(event["data"]))
        
    async def friend_request_cancel(self, event):
        # Send the friend request update to the client
        await self.send(text_data=json.dumps(event["data"]))

    async def disconnect(self, close_code):
        # Remove the user from the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

