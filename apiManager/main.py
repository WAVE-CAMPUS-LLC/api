import os
import django
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()


# from apiManager.apps.accountManagementApp.apiLogic import router as account_router
# from apiManager.apps.eventManagementApp.apiLogic import router as event_router
from apiManager.apps.authenticationApp.apiLogic import router as auth_router
# from apiManager.apps.eventTicketsApp.apiLogic import router as ticket_router
# from apiManager.apps.socialApp.apiLogic import router as social_router


app = FastAPI(title="WAVE. API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# app.include_router(account_router, prefix="/waveYourCampusAPIFromOAK/account", tags=["Account"])
# app.include_router(event_router, prefix="/waveYourCampusAPIFromOAK/event", tags=["Event"])
app.include_router(auth_router, prefix="/waveYourCampusAPIFromOAK/auth", tags=["Authentication"]) 
# app.include_router(ticket_router, prefix="/waveYourCampusAPIFromOAK/ticket", tags=["Ticket"])
# app.include_router(social_router, prefix="/waveYourCampusAPIFromOAK/social", tags=["Social"])