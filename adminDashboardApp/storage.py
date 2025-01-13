from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from supabase import create_client
import mimetypes
import os
from dotenv import load_dotenv
from io import BytesIO
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "wave")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Supabase credentials are not set!")

# Create a Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise



class SupabaseStorage(Storage):
    def __init__(self, bucket_name=SUPABASE_BUCKET):
        logger.info(f"Initializing SupabaseStorage with bucket: {bucket_name}")
        self.bucket_name = bucket_name
        
        # Verify bucket exists
        try:
            logger.info("Attempting to list buckets")
            buckets = supabase.storage.list_buckets()
            logger.info(f"Available buckets: {buckets}")
            
            if not any(bucket.name == bucket_name for bucket in buckets):
                logger.error(f"Bucket {bucket_name} not found. Please create it in Supabase dashboard")
                raise ValueError(f"Bucket {bucket_name} does not exist in Supabase project")
            
            logger.info(f"Successfully verified bucket {bucket_name} exists")
                
        except Exception as e:
            logger.error(f"Error verifying bucket {bucket_name}: {str(e)}", exc_info=True)
            raise

    def _save(self, name, content):
        logger.info(f"Starting _save method for file: {name}")
        try:
            # Ensure consistent file path formatting
            name = self._normalize_name(name)
            
            # If content is a File or UploadedFile object, read its content
            if hasattr(content, 'read'):
                content.seek(0)
                file_content = content.read()
            else:
                file_content = content
            
            # Get the content type
            content_type, _ = mimetypes.guess_type(name)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Upload file to Supabase
            try:
                response = supabase.storage.from_(self.bucket_name).upload(
                    path=name,
                    file=file_content,
                    file_options={"contentType": content_type, "upsert": True}
                )
                logger.info(f"Upload response: {response}")
                return name
                
            except Exception as upload_error:
                logger.error(f"Supabase upload error for file {name}", exc_info=True)
                raise upload_error

        except Exception as e:
            logger.error(f"Error in _save method for file {name}", exc_info=True)
            raise

    def _normalize_name(self, name):
        """
        Normalize the file path to ensure consistent formatting
        """
        return os.path.normpath(name).replace('\\', '/')

    def url(self, name):
        return supabase.storage.from_(self.bucket_name).get_public_url(name)

    def exists(self, name):
        logger.info(f"Checking if file exists in bucket {self.bucket_name}: {name}")
        try:
            # List objects in the bucket
            response = supabase.storage.from_(self.bucket_name).list()
            logger.info(f"List objects response: {response}")

            # Ensure response is iterable (list of objects)
            return any(item.get("name") == name for item in response)
        except Exception as e:
            logger.error(f"Error checking file existence in bucket {self.bucket_name}: {str(e)}", exc_info=True)
            return False


    def delete(self, name):
        response = supabase.storage.from_(self.bucket_name).remove([name])
        if response.get("error"):
            raise ValueError(f"Failed to delete file from Supabase: {response['error']}")

    def _open(self, name, mode='rb'):
        """
        Required method for Django storage class
        """
        logger.debug(f"Opening file {name} in mode {mode}")
        try:
            response = supabase.storage.from_(self.bucket_name).download(name)
            return BytesIO(response)
        except Exception as e:
            logger.error(f"Error opening file {name}: {str(e)}")
            raise
 