from channels.generic.websocket import AsyncJsonWebsocketConsumer

class DashboardConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add('dashboard', self.channel_name)
        await self.accept()
    
    async def disconnect(self,close_code):
        await self.channel_layer.group_discard('dashboard', self.channel_name)
    
    async def receive_json(self,data):
        
        command = data["command"]

        try:
            if command == 'group_by':
                await self.group_by(data["data"])
        
        except ClientError as e:
            await self.send_json({"error" : e})
        
    async def group_by(self,data):
        pass

