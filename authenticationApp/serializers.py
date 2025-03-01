from rest_framework import serializers
from .models import CustomUser
from accountManagementApp.serializers import UserProfileSerializer

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

class CustomUserSerializer(serializers.ModelSerializer):
    user_profile = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 
                 'is_staff', 'birthday', 'age', 'is_suspended', 'is_superuser']
        read_only_fields = ['id', 'is_active', 'is_staff', 'is_suspended', 'is_superuser']

    def get_user_profile(self, obj):
        from accountManagementApp.serializers import UserProfileSerializer
        try:
            return UserProfileSerializer(obj.user_profile).data
        except:
            return None