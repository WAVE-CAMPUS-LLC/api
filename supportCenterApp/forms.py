from django import forms
from .models import SupportTicket, FeedbackModel

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["title", "email", "subject", "description"]
        
        

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = FeedbackModel
        fields = ["full_name", "email", "subject", "body"]