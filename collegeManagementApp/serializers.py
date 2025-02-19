from rest_framework import serializers
from adminDashboardApp.models import College
from eventManagementApp.models import Event


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = "__all__"
        
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"