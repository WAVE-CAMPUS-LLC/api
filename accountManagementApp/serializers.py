from rest_framework import serializers
from .models import UserProfile
from authenticationApp.serializers import CustomUserSerializer


class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = "__all__"