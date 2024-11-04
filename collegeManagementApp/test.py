# app/api/api_v1/endpoints/upload.py
import string
import boto3
import os
import random
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

# Load AWS credentials and region from environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
region_name = os.getenv('AWS_REGION')
bucket_name = os.getenv('AWS_BUCKET_NAME')

# Debugging: Print environment variables
print(f"AWS_ACCESS_KEY_ID: {aws_access_key_id}")
print(f"AWS_SECRET_ACCESS_KEY: {aws_secret_access_key}")
print(f"AWS_REGION: {region_name}")
print(f"AWS_BUCKET_NAME: {bucket_name}")


# S3 setup
s3 = boto3.client(
    's3',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name
)

def upload_image_to_s3(image_path):
    try:
        # Generate a random file name
        file_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.jpg'

        # Upload the file to S3
        s3.upload_file(image_path, bucket_name, file_name, ExtraArgs={'ContentType': 'image/jpeg'})

        # Get the S3 URL
        url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"

        return url

    except FileNotFoundError:
        print("The file was not found")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None
    except PartialCredentialsError:
        print("Incomplete credentials provided")
        return None
    except ClientError as e:
        print(f"Unexpected error: {e}")
        return None

# Test uploading an image
image_path = "C:\\Users\\davis\\OneDrive\\Desktop\\WAVE\\wave_v1\\college_logos\\swarthmore.jpeg"
uploaded_url = upload_image_to_s3(image_path)

if uploaded_url:
    print(f"Image successfully uploaded to: {uploaded_url}")
else:
    print("Image upload failed")