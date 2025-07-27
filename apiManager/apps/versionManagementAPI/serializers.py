from pydantic import BaseModel, Field


class VersionCheckResponse(BaseModel):
    """
    Response model for version check API.
    """

    latest_version: str
    minimum_required_version: str
    force_update: bool
