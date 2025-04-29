# /Users/owusunp/wave_v1-1/apiManager/apps/coreAPI/version_middleware.py

from fastapi import Request, status
from fastapi.responses import JSONResponse

class VersionCheckMiddleware:
    def __init__(
        self,
        minimum_ios_version: str = "1.0.4",
        minimum_android_version: str = "1.0.4",
        excluded_paths: list = None
    ):
        self.minimum_versions = {
            "ios": minimum_ios_version,
            "android": minimum_android_version
        }
        self.excluded_paths = excluded_paths or [
            "/api/ping",
            "/api/auth",
            "/swagger",
            "/docs",
            "/redoc"
        ]
    
    async def __call__(self, request: Request, call_next):
        # Skip version check for excluded paths
        for path in self.excluded_paths:
            if request.url.path.startswith(path):
                return await call_next(request)
        
        # Get app version from request headers
        app_version = request.headers.get("x-app-version")
        platform = request.headers.get("x-app-platform", "ios")
        
        # Skip check if headers not present
        if not app_version:
            return await call_next(request)
        
        # Check if version is below minimum required
        if self._is_version_less_than(app_version, self.minimum_versions.get(platform, "1.0.4")):
            return JSONResponse(
                status_code=status.HTTP_426_UPGRADE_REQUIRED,
                content={
                    "error": "Update Required",
                    "message": "Please update to the latest version to continue using the app.",
                    "appStoreUrl": "https://apps.apple.com/us/app/wave-oc/id6744196161",
                    "currentVersion": app_version,
                    "minimumVersion": self.minimum_versions.get(platform)
                }
            )
        
        # Continue to next middleware if version is OK
        return await call_next(request)
    
    def _is_version_less_than(self, version1: str, version2: str) -> bool:
        """Compare two version strings"""
        if not version1:
            return True
        
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        # Pad shorter version with zeros
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)
        
        for i in range(len(v1_parts)):
            if v1_parts[i] < v2_parts[i]:
                return True
            if v1_parts[i] > v2_parts[i]:
                return False
        
        return False  # Versions are equal