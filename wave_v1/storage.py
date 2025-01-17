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
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET")

if not SUPABASE_URL or not SUPABASE_API_KEY:
    raise ValueError("Supabase credentials are not set!")

# Create a Supabase client
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
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
                logger.error(
                    f"Bucket {bucket_name} not found. Please create it in Supabase dashboard"
                )
                raise ValueError(
                    f"Bucket {bucket_name} does not exist in Supabase project"
                )

            logger.info(f"Successfully verified bucket {bucket_name} exists")

        except Exception as e:
            logger.error(
                f"Error verifying bucket {bucket_name}: {str(e)}", exc_info=True
            )
            raise

    def _save(self, name, content):
        # Normalize the path to use forward slashes
        name = name.replace("\\", "/")

        logger.info(f"Starting _save method for file: {name}")
        try:
            # 1) Check if the file already exists. If so, remove it first.
            if self.exists(name):
                logger.info(f"File '{name}' already exists in bucket. Deleting it first.")
                self.delete(name)

            # 2) Read file content (handle File or UploadedFile object)
            logger.info(f"Content type: {type(content)}")
            if hasattr(content, "read"):
                content.seek(0)
                file_content = content.read()
            else:
                file_content = content

            # 3) Determine content type
            content_type, _ = mimetypes.guess_type(name)
            if not content_type:
                content_type = "application/octet-stream"

            logger.info(f"Determined content type: {content_type}")

            # 4) Upload file to Supabase
            logger.info("Attempting to upload to Supabase...")
            response = supabase.storage.from_(self.bucket_name).upload(
                path=name,
                file=file_content,
                file_options={"contentType": content_type},
            )
            logger.info(f"Upload response: {response}")

            logger.info(f"Successfully saved file: {name}")
            return name

        except Exception as e:
            logger.error(f"Error in _save method", exc_info=True)
            raise

    def url(self, name):
        # Normalize slashes before returning the public URL
        name = name.replace("\\", "/")
        return supabase.storage.from_(self.bucket_name).get_public_url(name)

    def exists(self, name):
        # Normalize the path
        name = name.replace("\\", "/")

        logger.info(f"Checking if file exists in bucket {self.bucket_name}: {name}")

        prefix = os.path.dirname(name)
        filename = os.path.basename(name)

        try:
            # List only objects in that prefix
            response = supabase.storage.from_(self.bucket_name).list(path=prefix)
            logger.info(f"List objects response: {response}")

            # Now check if any item in the prefix has a matching name
            for item in response:
                if item.get("name") == filename:
                    return True
            return False

        except Exception as e:
            logger.error(
                f"Error checking file existence in bucket {self.bucket_name}: {str(e)}",
                exc_info=True,
            )
            return False

    def delete(self, name):
        # Normalize the path
        name = name.replace("\\", "/")

        logger.info(f"Deleting file {name} from bucket {self.bucket_name}...")
        response = supabase.storage.from_(self.bucket_name).remove([name])
        logger.info(f"Delete response: {response}")

        # Supabase returns {'data': {...}, 'error': None} on success
        if response.get("error"):
            raise ValueError(
                f"Failed to delete file from Supabase: {response['error']}"
            )

    def _open(self, name, mode="rb"):
        # Normalize the path
        name = name.replace("\\", "/")

        logger.debug(f"Opening file {name} in mode {mode}")
        try:
            response = supabase.storage.from_(self.bucket_name).download(name)
            return BytesIO(response)
        except Exception as e:
            logger.error(f"Error opening file {name}: {str(e)}")
            raise
