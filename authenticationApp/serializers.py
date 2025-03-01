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
            
            # Get the profile object
            profile = obj.user_profile
            
            # Convert model instance to dictionary
            profile_dict = model_to_dict(profile, exclude=['user'])
            
            # Handle file fields (like profile_photo, cover_photo) which aren't properly serialized by model_to_dict
            if hasattr(profile, 'profile_photo') and profile.profile_photo:
                profile_dict['profile_photo'] = profile.profile_photo.url
                
            if hasattr(profile, 'profile_qr_code') and profile.profile_qr_code:
                profile_dict['profile_qr_code'] = profile.profile_qr_code.url
                
                
            return profile_dict
        return None