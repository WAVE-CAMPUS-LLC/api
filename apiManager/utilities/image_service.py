"""
Centralized image service for handling event image operations.
This service provides a clean, type-safe interface for image uploads and management.
"""

import os
import uuid
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from starlette.datastructures import FormData, UploadFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.conf import settings

from eventManagementApp.models import Event
from authenticationApp.models import CustomUser


class ImageValidationError(Exception):
    """Custom exception for image validation errors."""

    pass


class ImageService:
    """Centralized service for handling event image operations."""

    # Supported image formats
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Image field mappings for events
    EVENT_IMAGE_FIELDS = {
        "header_photo": "event_images/header/",
        "body_photo_one": "event_images/body/one/",
        "body_photo_two": "event_images/body/two/",
        "body_photo_three": "event_images/body/three/",
        "body_photo_four": "event_images/body/four/",
        "body_photo_five": "event_images/body/five/",
    }

    @classmethod
    def validate_image_file(cls, file: UploadFile, field_name: str) -> None:
        """
        Validate an uploaded image file.

        Args:
            file: The uploaded file to validate
            field_name: Name of the field for error messages

        Raises:
            ImageValidationError: If validation fails
        """
        if not file or not file.filename:
            raise ImageValidationError(f"{field_name} is required")

        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in cls.SUPPORTED_FORMATS:
            raise ImageValidationError(
                f"{field_name} must be one of: {', '.join(cls.SUPPORTED_FORMATS)}"
            )

        # Check content type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise ImageValidationError(f"{field_name} must be a valid image file")

    @classmethod
    async def convert_to_django_file(cls, file: UploadFile) -> SimpleUploadedFile:
        """
        Convert FastAPI UploadFile to Django SimpleUploadedFile.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Django SimpleUploadedFile object

        Raises:
            ImageValidationError: If conversion fails
        """
        try:
            content = await file.read()

            # Validate file size
            if len(content) > cls.MAX_FILE_SIZE:
                raise ImageValidationError(
                    f"File size exceeds maximum limit of {cls.MAX_FILE_SIZE // (1024*1024)}MB"
                )

            return SimpleUploadedFile(
                name=file.filename or "uploaded_file",
                content=content,
                content_type=file.content_type or "application/octet-stream",
            )
        except Exception as e:
            raise ImageValidationError(f"Error processing file: {str(e)}")

    @classmethod
    def generate_unique_filename(cls, original_filename: str, field_name: str) -> str:
        """
        Generate a unique filename for uploaded images.

        Args:
            original_filename: Original filename from upload
            field_name: Field name for organizing uploads

        Returns:
            Unique filename with timestamp and UUID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        ext = Path(original_filename).suffix.lower()

        return f"{field_name}_{timestamp}_{unique_id}{ext}"

    @classmethod
    async def process_event_images(
        cls,
        form_data: Union[Dict[str, Any], FormData],
        allowed_fields: Optional[List[str]] = None,
    ) -> Dict[str, SimpleUploadedFile]:
        """
        Process multiple event image uploads from form data.

        Args:
            form_data: Form data containing image uploads
            allowed_fields: List of allowed image field names (defaults to all)

        Returns:
            Dictionary mapping field names to processed Django files

        Raises:
            ImageValidationError: If any image validation fails
        """
        if allowed_fields is None:
            allowed_fields = list(cls.EVENT_IMAGE_FIELDS.keys())

        processed_files = {}

        for field_name in allowed_fields:
            if field_name not in cls.EVENT_IMAGE_FIELDS:
                continue

            file_value = form_data.get(field_name)

            # Skip if no file provided or not an UploadFile
            if (
                not file_value
                or not isinstance(file_value, UploadFile)
                or not file_value.filename
            ):
                continue

            # Validate the image
            cls.validate_image_file(file_value, field_name)

            # Convert to Django file
            django_file = await cls.convert_to_django_file(file_value)

            # Generate unique filename
            unique_filename = cls.generate_unique_filename(
                file_value.filename, field_name
            )
            django_file.name = unique_filename

            processed_files[field_name] = django_file

        return processed_files

    @classmethod
    def update_event_images(
        cls, event: Event, processed_files: Dict[str, SimpleUploadedFile]
    ) -> Dict[str, Optional[str]]:
        """
        Update event with new images and return URLs.

        Args:
            event: Event instance to update
            processed_files: Dictionary of processed image files

        Returns:
            Dictionary mapping field names to image URLs
        """
        updated_urls = {}

        for field_name, django_file in processed_files.items():
            if hasattr(event, field_name):
                # Delete old image if it exists
                old_image = getattr(event, field_name)
                if old_image:
                    try:
                        old_image.delete(save=False)
                    except Exception as e:
                        print(f"Warning: Could not delete old {field_name}: {e}")

                # Save new image
                setattr(event, field_name, django_file)
                updated_urls[field_name] = django_file.name

        # Save the event
        event.save()

        # Return URLs for updated images
        result = {}
        for field_name in updated_urls:
            current_image = getattr(event, field_name)
            if current_image:
                result[field_name] = current_image.url

        return result

    @classmethod
    def delete_event_image(cls, event: Event, field_name: str) -> bool:
        """
        Delete a specific image from an event.

        Args:
            event: Event instance
            field_name: Name of the image field to delete

        Returns:
            True if image was deleted, False if no image existed
        """
        if not hasattr(event, field_name):
            return False

        current_image = getattr(event, field_name)
        if not current_image:
            return False

        try:
            current_image.delete(save=False)
            setattr(event, field_name, None)
            event.save()
            return True
        except Exception as e:
            print(f"Error deleting {field_name}: {e}")
            return False

    @classmethod
    def get_event_image_urls(cls, event: Event) -> Dict[str, Optional[str]]:
        """
        Get all image URLs for an event.

        Args:
            event: Event instance

        Returns:
            Dictionary mapping field names to URLs (None if no image)
        """
        urls = {}
        for field_name in cls.EVENT_IMAGE_FIELDS:
            if hasattr(event, field_name):
                image = getattr(event, field_name)
                urls[field_name] = image.url if image else None
        return urls


class EventImageHandler:
    """High-level handler for event image operations."""

    @classmethod
    async def handle_header_photo_update(
        cls, event: Event, form_data: Dict
    ) -> Dict[str, str]:
        """
        Handle header photo update for an event.

        Args:
            event: Event instance
            form_data: Form data containing the header photo

        Returns:
            Response data with success message and URL
        """
        try:
            # Process header photo
            processed_files = await ImageService.process_event_images(
                form_data, allowed_fields=["header_photo"]
            )

            if not processed_files:
                raise ImageValidationError("Header photo is required")

            # Update event
            urls = ImageService.update_event_images(event, processed_files)

            return {
                "message": "Event header photo updated successfully",
                "eventId": str(event.eventId),
                "header_photo_url": urls.get("header_photo"),
            }

        except ImageValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @classmethod
    async def handle_body_photos_update(
        cls, event: Event, form_data: Dict
    ) -> Dict[str, Union[str, Dict]]:
        """
        Handle body photos update for an event.

        Args:
            event: Event instance
            form_data: Form data containing body photos

        Returns:
            Response data with success message and URLs
        """
        try:
            # Process body photos
            processed_files = await ImageService.process_event_images(
                form_data,
                allowed_fields=[
                    "body_photo_one",
                    "body_photo_two",
                    "body_photo_three",
                    "body_photo_four",
                    "body_photo_five",
                ],
            )

            if not processed_files:
                raise ImageValidationError("At least one valid body photo is required")

            # Update event
            urls = ImageService.update_event_images(event, processed_files)

            return {
                "message": "Event body photos updated successfully",
                "eventId": str(event.eventId),
                "updated_photos": urls,
            }

        except ImageValidationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @classmethod
    def validate_event_ownership(cls, event: Event, user_id: int) -> None:
        """
        Validate that a user owns the event.

        Args:
            event: Event instance
            user_id: User ID to validate

        Raises:
            HTTPException: If user doesn't own the event
        """
        if event.host.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this event. Only the event host can edit images.",
            )
