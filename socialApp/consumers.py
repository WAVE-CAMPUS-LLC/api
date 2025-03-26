from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async

class FriendRequestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection if the user is not authenticated
            await self.close()
            return
            
        self.group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
    async def friend_request_action(self, event):
        # Send the friend request update to the client
        await self.send(text_data=json.dumps(event["data"]))

    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

class SocialHomeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection if the user is not authenticated
            await self.close()
            return
            
        # Authenticate the user and create a group based on the user ID
        self.group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def social_update(self, event):
        # Send the friend request update to the client
        await self.send(text_data=json.dumps(event["data"]))

    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:
            # Remove the user from the group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        
class CrewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection if the user is not authenticated
            await self.close()
            return
            
        # Authenticate the user and create a group based on the user ID
        self.group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def crew_request_update(self, event):
        # Send the friend request update to the client
        await self.send(text_data=json.dumps(event["data"]))

    async def disconnect(self, close_code):
        if not self.scope["user"].is_anonymous:
            # Remove the user from the group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
