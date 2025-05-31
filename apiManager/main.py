# /Users/owusunp/wave_v1-1/apiManager/main.py
import os
import django

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from apiManager.apps.coreAPI.apiLogic import router as core
from apiManager.apps.accountManagementAPI.apiLogic import router as account_router
from apiManager.apps.eventManagementAPI.apiLogic import router as event_router
from apiManager.apps.authenticationAPI.apiLogic import router as auth_router
from apiManager.apps.collegeManagementAPI.apiLogic import router as college_router
from apiManager.apps.eventTicketsAPI.apiLogic import router as ticket_router
from apiManager.apps.adminManagementAPI.apiLogic import router as admin_router

from apiManager.apps.coreAPI.version_middleware import VersionCheckMiddleware

app = FastAPI(title="WAVE. API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# instantiate once with your min-versions and exact prefixes
version_checker = VersionCheckMiddleware(
    minimum_ios_version="1.0.4",
    minimum_android_version="1.0.4",
    excluded_paths=[
        "/waveYourCampusAPIFromOAK/auth",
        "/waveYourCampusAPIFromOAK/core/ping",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)


@app.middleware("http")
async def enforce_version(request: Request, call_next):
    # this will run BEFORE any router, and short-circuit old clients with 426
    return await version_checker(request, call_next)


# now mount your routers
app.include_router(core, prefix="/waveYourCampusAPIFromOAK/core", tags=["Core"])
app.include_router(
    account_router, prefix="/waveYourCampusAPIFromOAK/account", tags=["Account"]
)
app.include_router(
    event_router, prefix="/waveYourCampusAPIFromOAK/host", tags=["Event"]
)
app.include_router(
    college_router, prefix="/waveYourCampusAPIFromOAK/colleges", tags=["College"]
)
app.include_router(
    auth_router, prefix="/waveYourCampusAPIFromOAK/auth", tags=["Authentication"]
)
app.include_router(
    ticket_router, prefix="/waveYourCampusAPIFromOAK/ticket", tags=["Ticket"]
)
app.include_router(
    admin_router, prefix="/waveYourCampusAPIFromOAK/admin", tags=["Admin"]
)
