from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync,sync_to_async
import json
from .models import * 
from channels.db import database_sync_to_async

class OrderProgress(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = 'order_%s' % self.room_name

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        
        self.accept()
 
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
    
    def receive(self, text_data):
        datapoint = json.loads(text_data)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,{
                'type' : 'order_status',
                'payload' : data
            }    
        )

    def order_status(self,event):
        print(event)
        data = event['payload']
        self.send(text_data=json.dumps({'payload':data}))

    