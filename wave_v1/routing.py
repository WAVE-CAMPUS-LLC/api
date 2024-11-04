from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import your_app_name.routing  # Replace with your actual app name

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            wave_v1.routing.websocket_urlpatterns
        )
    ),
})
