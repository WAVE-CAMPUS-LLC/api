import os 
from firebase_admin import credentials, initialize_app, storage
from django.conf import settings
from django.core.files.storage import Storage
from urllib.parse import quote


FIREBASE_CONFIG = os.path.join(settings.BASE_DIR, "firebase.json")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "wave-be2d0.appspot.com")


if not hasattr(settings, "FIREBASE_INITIALIZED"):
    if os.path.exists(FIREBASE_CONFIG):
        cred = credentials.Certificate(FIREBASE_CONFIG)
        initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})
        settings.FIREBASE_INITIALIZED = True
    else:
        print("Firebase credentials file not found. Please check the path.")
        raise ValueError("Firebase credentials file not found. Please check the path.")


class FirebaseStorage(Storage):
    def __init__(self, *args, **kwargs):
        self.bucket = storage.bucket()
    
    def _save(self, name, content):
        # Clean the file name to prevent issues
        name = self._clean_name(name)
        
        # Create blob and upload the file
        blob = self.bucket.blob(name)
        content.seek(0)  # Ensure we're at the start of the file
        blob.upload_from_file(content.file)
        blob.make_public()  # Make the file publicly accessible
        
        return name
    
    def _clean_name(self, name):
        """
        Clean the file name to make it safe for Firebase Storage
        """
        return os.path.normpath(name).replace('\\', '/')
    
    def url(self, name):
        """
        Get the public URL for accessing the file
        """
        if not name:
            return None
            
        blob = self.bucket.blob(name)
        if not blob.exists():
            return None
            
        # URL encode the file name to handle special characters
        encoded_name = quote(name)
        return f"https://firebasestorage.googleapis.com/v0/b/{settings.FIREBASE_STORAGE_BUCKET}/o/{encoded_name}?alt=media"
    
    def exists(self, name):
        blob = self.bucket.blob(self._clean_name(name))
        return blob.exists()
    
    def size(self, name):
        blob = self.bucket.blob(self._clean_name(name))
        return blob.size if blob.exists() else 0
    
    def delete(self, name):
        blob = self.bucket.blob(self._clean_name(name))
        if blob.exists():
            blob.delete()
