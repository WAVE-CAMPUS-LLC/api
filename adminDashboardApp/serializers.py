from rest_framework import serializers
from .models import College


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = [
            "name",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "contact_website",
            "motto",
            "logo",
            "campus_image",
        ]
