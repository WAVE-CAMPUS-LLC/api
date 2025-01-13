from supabase import create_client
from dotenv import load_dotenv
import os
import mimetypes

# Load environment variables from .env
load_dotenv()

# Retrieve Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

if not SUPABASE_URL or not SUPABASE_API_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_API_KEY is not set!")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)

# Example: Uploading a file
file_path = "static/images/career/careers.png"
bucket_name = "wave"
file_name = "uploads/image.png"

with open(file_path, "rb") as file_data:
    content_type, _ = mimetypes.guess_type(file_path)
    response = supabase.storage.from_(bucket_name).upload(file_name, file_data, {"content-type": content_type})

print(response)
