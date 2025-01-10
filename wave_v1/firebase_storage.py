import os 
from firebase_admin import credentials, initialize_app, storage
from django.conf import settings
from django.core.files.storage import Storage
from urllib.parse import urljoin


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
        blob = self.bucket.blob(name)
        blob.upload_from_file(content.file)
        blob.make_public()
        return blob.name
    
    def url(self, name):
        blob = self.bucket.blob(name)
        if not blob.exists():
            raise FileNotFoundError(f"File not found in Firebase Storage: {name}")
        return blob.public_url
    
    def delete(self, name):
        blob = self.bucket.blob(name)
        blob.delete()
        
    def exists(self, name):
        blob = self.bucket.blob(name)
        return blob.exists()
    
    def size(self, name):
        blob = self.bucket.blob(name)
        return blob.size
