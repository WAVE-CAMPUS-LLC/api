from supabase import create_client
import os

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)

def upload_to_supabase(bucket_name, file_path, destination_path):
    """
    Upload a file to Supabase storage.

    :param bucket_name: The name of the Supabase bucket.
    :param file_path: Local path to the file.
    :param destination_path: Path in the bucket to store the file.
    :return: Public URL of the uploaded file (if the bucket is public).
    """
    with open(file_path, "rb") as file:
        try:
            response = supabase.storage.from_(bucket_name).upload(destination_path, file)
            return supabase.storage.from_(bucket_name).get_public_url(destination_path)
        except Exception as e:
            raise Exception(f"Error uploading file: {str(e)}")
