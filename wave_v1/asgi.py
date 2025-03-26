import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wave_v1.settings')

application = get_asgi_application()

import supportCenterApp.routing
import socialApp.routing
import adminDashboardApp.routing

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                supportCenterApp.routing.websocket_urlpatterns +
                socialApp.routing.websocket_urlpatterns +
                adminDashboardApp.routing.websocket_urlpatterns
            )
        )
    ),
})
