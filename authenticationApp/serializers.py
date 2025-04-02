from rest_framework import serializers
from .models import CustomUser

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_active', 
                 'is_staff', 'age', 'is_suspended', 'is_superuser']
        read_only_fields = ['id', 'is_active', 'is_staff', 'is_suspended', 'is_superuser']