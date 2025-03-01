from rest_framework import serializers
from .models import CustomUser

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

class CustomUserSerializer(serializers.ModelSerializer):
    user_profile = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 
                 'is_staff', 'birthday', 'age', 'is_suspended', 'is_superuser', 'user_profile']
        read_only_fields = ['id', 'is_active', 'is_staff', 'is_suspended', 'is_superuser']

    def get_user_profile(self, obj):
        """
        Get the user profile data without creating a circular import
        """
        # Only try to get profile if it exists
        if hasattr(obj, 'user_profile'):
            # Import here to avoid circular imports
            from accountManagementApp.models import UserProfile
            from django.forms.models import model_to_dict
            from django.db.models.fields.files import FieldFile
            
            # Get the profile object
            profile = obj.user_profile
            
            try:
                # Convert model instance to dictionary
                profile_dict = model_to_dict(profile, exclude=['user'])
                
                # Process all fields to ensure they're JSON serializable
                for field_name, value in profile_dict.items():
                    # Handle file fields
                    if isinstance(value, FieldFile) and value:
                        try:
                            profile_dict[field_name] = value.url
                        except ValueError:
                            profile_dict[field_name] = None
                    
                    # Handle any other non-serializable types
                    elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict, tuple)):
                        try:
                            profile_dict[field_name] = model_to_dict(value)
                        except:
                            profile_dict[field_name] = str(value)
                
                return profile_dict
            except Exception as e:
                # Fallback to basic serialization if model_to_dict fails
                return {
                    'id': profile.id,
                    'profile_photo': profile.profile_photo.url if hasattr(profile, 'profile_photo') and profile.profile_photo else None,
                    'profile_qr_code': profile.profile_qr_code.url if hasattr(profile, 'profile_qr_code') and profile.profile_qr_code else None,
                }
        return None