from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
from app.Authentication import GridAuthMiddleware

import app.routing

application = ProtocolTypeRouter({
    'websocket' : GridAuthMiddleware(
        URLRouter(
            app.routing.websocket_urlpatterns
        )
    ),
})