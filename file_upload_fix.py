# This file contains the necessary changes to fix the profile photo upload issue
# in apiManager/apps/accountManagementAPI/apiLogic.py

# Replace the section in update_settings_async function where it handles standard file upload
# Look for "Check for standard file upload" comment and replace that section with this code:

# Check for standard file upload
if files and "profile_photo" in files:
    print("[update_settings_async] Standard file upload")
    
    upload_file = files["profile_photo"]
    
    # Read file content
    file_content = upload_file.file.read()
    
    # Import ContentFile
    from django.core.files.base import ContentFile
    
    # Delete old photo if exists
    if profile.profile_photo:
        try:
            profile.profile_photo.delete(save=False)
        except Exception as e:
            print(f"Error deleting old photo: {e}")
    
    # Directly save to profile model
    profile.profile_photo.save(
        upload_file.filename,
        ContentFile(file_content),
        save=True
    )
    
    # Return success response
    serializer = UserProfileSerializer(profile)
    return {
        "message": "Profile picture updated successfully!",
        "profile": serializer.data,
    }
