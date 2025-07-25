import os
import uuid
from PIL import Image
from django.conf import settings


def generate_profile_picture(first_name, last_name, width=200, height=200):
    """
    Generate a simple profile picture with initials.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple colored background
        bg_color = (70, 130, 180)  # Steel blue
        text_color = (255, 255, 255)  # White
        
        # Create image
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Get initials
        initials = ""
        if first_name:
            initials += first_name[0].upper()
        if last_name:
            initials += last_name[0].upper()
        
        if not initials:
            initials = "U"  # Default
        
        # Try to use a font, fall back to default if not available
        try:
            font_size = min(width, height) // 3
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate text position (center)
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text
        draw.text((x, y), initials, fill=text_color, font=font)
        
        return img
        
    except Exception as e:
        print(f"Error generating profile picture: {e}")
        return None


def generate_universal_qr_code_for_user(user_profile):
    """
    Utility function to generate a universal QR code for a specific user profile.
    
    Args:
        user_profile: UserProfile instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not user_profile or not user_profile.user:
            return False
        
        success = user_profile.generate_universal_qr_code()
        
        if success:
            user_profile.save(update_fields=['universal_qr_code_image'])
            return True
        else:
            return False
        
    except Exception as e:
        # Log error for production monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating QR code for user {user_profile.user.username if user_profile.user else 'unknown'}: {e}")
        return False


def bulk_generate_universal_qr_codes(user_profiles_queryset, batch_size=50):
    """
    Utility function to generate universal QR codes for multiple users in batches.
    
    Args:
        user_profiles_queryset: QuerySet of UserProfile objects
        batch_size: Number of profiles to process at once
        
    Returns:
        dict: Statistics about the operation
    """
    total_count = user_profiles_queryset.count()
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for i in range(0, total_count, batch_size):
        batch = user_profiles_queryset[i:i + batch_size]
        
        for profile in batch:
            try:
                # Skip if QR code already exists
                if profile.universal_qr_code_image:
                    skipped_count += 1
                    continue
                
                success = generate_universal_qr_code_for_user(profile)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                # Log error for production monitoring
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error processing {profile.user.username}: {e}")
        
        processed = min(i + batch_size, total_count)
    
    return {
        'total': total_count,
        'success': success_count,
        'errors': error_count,
        'skipped': skipped_count
    }
