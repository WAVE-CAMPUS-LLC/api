"""
College lookup utility for resolving colleges from email domains.

This module provides functionality to find existing colleges or create new ones
using AI-powered domain analysis through WALLE AI.
"""

import os
import sys
import django
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from typing import Optional

# Add project root to Python path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup Django when run as standalone script
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wave_v1.settings")
django.setup()

from adminDashboardApp.models import College
from apiManager.utilities.extract_email import extract_email_domain
from apiManager.utilities.walle import call_walle_ai


def download_image(
    image_url: str, college_name: str, image_type: str = "logo"
) -> Optional[ContentFile]:
    """
    Download college image (logo or campus photo) from URL and return as ContentFile.

    Args:
        image_url (str): URL of the image
        college_name (str): Name of the college for filename
        image_type (str): Type of image - "logo" or "campus"

    Returns:
        Optional[ContentFile]: Downloaded image as Django ContentFile, or None if failed
    """
    try:
        print(f"🖼️ Downloading {image_type} from: {image_url}")

        # Set headers to mimic browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(image_url, headers=headers, timeout=15)
        response.raise_for_status()

        if response.status_code == 200:
            # Get file extension from URL or content type
            parsed_url = urlparse(image_url)
            file_extension = os.path.splitext(parsed_url.path)[1]

            if not file_extension:
                content_type = response.headers.get("content-type", "")
                if "png" in content_type:
                    file_extension = ".png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    file_extension = ".jpg"
                else:
                    file_extension = ".jpg"  # default for campus images

            # Create safe filename
            safe_name = "".join(
                c for c in college_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            safe_name = safe_name.replace(" ", "_")
            filename = f"{safe_name}_{image_type}{file_extension}"

            print(f"✅ {image_type.title()} downloaded successfully: {filename}")
            return ContentFile(response.content, name=filename)

    except Exception as e:
        print(f"❌ Error downloading {image_type}: {e}")
        return None


def resolve_or_create_college_from_email(email: str, created_by=None):
    """
    Resolve or create a college from an email domain.

    Args:
        email (str): Email to extract domain from
        created_by: User who created the college (optional)

    Returns:
        College: The existing or newly created college
    """
    try:
        root_domain = extract_email_domain(email)

        # Try to find existing college
        college = College.objects.filter(email_domain__iexact=root_domain).first()
        if college:
            print(f"🎓 Found existing college: {college.name}")
            return college

        print(f"🎓 No college found for domain: {root_domain}. Triggering WALLE.AI...")

        # Use WALLE AI to get college data
        college_data = call_walle_ai(domain=root_domain)

        # Create new college
        new_college = College.objects.create(
            name=college_data["name"],
            address=college_data.get("address", ""),
            city=college_data.get("city", ""),
            state=college_data.get("state", ""),
            zip_code=college_data.get("zip", ""),
            country=college_data.get("country", "USA"),
            motto=college_data.get("motto", ""),
            contact_website=college_data.get("website", ""),
            email_domain=root_domain,
            created_by=created_by,
            created_by_walleai=True,
        )

        # Download and save logo if provided
        logo_url = college_data.get("logo_url")
        if logo_url:
            logo_file = download_image(logo_url, college_data["name"], "logo")
            if logo_file:
                new_college.logo.save(logo_file.name, logo_file, save=True)
                print(f"🖼️ Logo saved for {new_college.name}")
            else:
                print(f"⚠️ Could not download logo for {new_college.name}")

        # Download and save campus image if provided
        campus_image_url = college_data.get("campus_image_url")
        if campus_image_url:
            campus_file = download_image(
                campus_image_url, college_data["name"], "campus"
            )
            if campus_file:
                new_college.campus_image.save(campus_file.name, campus_file, save=True)
                print(f"🏫 Campus image saved for {new_college.name}")
            else:
                print(f"⚠️ Could not download campus image for {new_college.name}")

        print(f"✅ Created new college: {new_college.name}")
        return new_college

    except Exception as e:
        print(f"❌ Error in resolve_or_create_college_from_email: {e}")
        raise e
