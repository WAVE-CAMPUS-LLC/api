from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import ContentFile
import requests
import os
from urllib.parse import urljoin
import uuid

class SupabaseStorage(Storage):
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_KEY
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.key}',
            'apikey': self.key,
        }

    def _save(self, name, content):
        # Generate a unique filename to prevent collisions
        ext = os.path.splitext(name)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        # Get the file content
        content.seek(0)
        file_data = content.read()

        # Upload to Supabase Storage
        url = f"{self.url}/storage/v1/object/{self.bucket}/{unique_filename}"
        response = requests.post(
            url,
            headers=self._get_headers(),
            data=file_data
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to upload to Supabase Storage: {response.text}")
        
        return unique_filename

    def _open(self, name, mode='rb'):
        url = f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to retrieve file from Supabase Storage: {response.text}")
        return ContentFile(response.content)

    def delete(self, name):
        url = f"{self.url}/storage/v1/object/{self.bucket}/{name}"
        response = requests.delete(url, headers=self._get_headers())
        return response.status_code == 200

    def exists(self, name):
        url = f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"
        response = requests.head(url)
        return response.status_code == 200

    def url(self, name):
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"

    def size(self, name):
        url = f"{self.url}/storage/v1/object/public/{self.bucket}/{name}"
        response = requests.head(url)
        return int(response.headers.get('content-length', 0))

    def get_available_name(self, name, max_length=None):
        return name  # We're using UUID for filenames, so no need to check for duplicates 