import json

from django.contrib.auth.models import User
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import Room, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        print(data)
        if 'message' in data:
            # Handle text message
            message = data['message']
            username = data['username']
            room = data['room']

            await self.save_message(username, room, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username
                }
            )
        elif 'attachment' in data:
            # Handle attachment
            attachment_data = data['attachment']
            username = data['username']
            room = data['room']

            await self.save_attachment(username, room, attachment_data)

            # Broadcast a message indicating that an attachment is received (if needed)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_attachment',
                    'username': username
                }
            )
    
    def save_attachment(self, username, room, attachment_data):
        user = User.objects.get(username=username)
        room = Room.objects.get(slug=room)

        # Save the attachment to the appropriate directory
        file_type = attachment_data['type']
        file_content = attachment_data['content']

        if file_type == 'image':
            file_path = f'root/picture/{username}_{room}_{datetime.now()}.png'
        elif file_type == 'video':
            file_path = f'root/video/{username}_{room}_{datetime.now()}.mp4'

        with open(file_path, 'wb') as file:
            file.write(base64.b64decode(file_content))

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        username = event['username']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

    @sync_to_async
    def save_message(self, username, room, message):
        user = User.objects.get(username=username)
        room = Room.objects.get(slug=room)

        Message.objects.create(user=user, room=room, content=message)