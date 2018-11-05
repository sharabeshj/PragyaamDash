from channels.generic.websocket import AsyncJsonWebsocketConsumer

class DashboardConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add('dashboard', self.channel_name)
        await self.accept()
    
    async def disconnect(self,close_code):
        await self.channel_layer.group_discard('dashboard', self.channel_name)
    
    async def receive(self,data):
        pass
        