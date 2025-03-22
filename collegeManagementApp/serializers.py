from rest_framework import serializers
from adminDashboardApp.models import College
from eventManagementApp.models import Event
from .models import OrganizationMembership, Organization

from accountManagementApp.serializers import UserProfileSerializer


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = "__all__"
        
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        
class OrganizationMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = "__all__"
        
class OrganizationSerializer(serializers.ModelSerializer):
    college = CollegeSerializer(read_only=True)
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Organization
        fields = "__all__"