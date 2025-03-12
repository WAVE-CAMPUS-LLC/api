from django import forms
from .models import HostApplication, Event, HostProfile
from django.utils.translation import gettext_lazy as _
from .models import Event, CouponCode
from adminDashboardApp.models import College
from accountManagementApp.models import UserProfile
from collegeManagementApp.models import OrganizationMembership, Organization


class HostApplicationForm(forms.ModelForm):    
    EVENT_TYPE_CHOICES = [
        ("Academic", "Academic"),
        ("Adventure", "Adventure"),
        ("Art", "Art"),
        ("Conference", "Conference"),
        ("Dance", "Dance"),
        ("Exhibition", "Exhibition"),
        ("Fashion", "Fashion"),
        ("Fundraiser", "Fundraiser"),
        ("Greek", "Greek"),
        ("Health", "Health"),
        ("Music", "Music"),
        ("Networking", "Networking"),
        ("Photography", "Photography"),
        ("Social", "Social"),
        ("Spiritual", "Spiritual"),
        ("Sports", "Sports"),
        ("Technology", "Technology"),
        ("Volunteer", "Volunteer"),
        ("Workshop", "Workshop"),
    ]

    eventTypes = forms.MultipleChoiceField(
        choices=EVENT_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="What type of events do you want to host?",
    )

    class Meta:
        model = HostApplication
        fields = [
            "firstName",
            "lastName",
            "email",
            "phone",
            "organizationName",
            "organizationEmail",
            "organizationLocation",
            "eventTypes",
            "eventHostedAnnually",
            "eventPopulation",
        ]
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["firstName"].initial = user.first_name
            self.fields["lastName"].initial = user.last_name
            self.fields["email"].initial = user.email
            self.fields["firstName"].disabled = True
            self.fields["lastName"].disabled = True
            self.fields["email"].disabled = True


class EventForm(forms.ModelForm):
    crew_discount = forms.BooleanField(required=False)
    show_guest_list = forms.BooleanField(required=False)
    couponsActivated = forms.BooleanField(required=False)
    forAllDisplay = forms.BooleanField(
        required=False, 
        initial=True,
        label=_("Make event discoverable by all?")
    )
    forCollegesDisplay = forms.BooleanField(
        required=False, 
        initial=False,
        label=_("Make event discoverable in colleges?"),
    )

    
    STATE_CHOICES = [
        ("AL", "Alabama"),
        ("AK", "Alaska"),
        ("AZ", "Arizona"),
        ("AR", "Arkansas"),
        ("CA", "California"),
        ("CO", "Colorado"),
        ("CT", "Connecticut"),
        ("DE", "Delaware"),
        ("FL", "Florida"),
        ("GA", "Georgia"),
        ("HI", "Hawaii"),
        ("ID", "Idaho"),
        ("IL", "Illinois"),
        ("IN", "Indiana"),
        ("IA", "Iowa"),
        ("KS", "Kansas"),
        ("KY", "Kentucky"),
        ("LA", "Louisiana"),
        ("ME", "Maine"),
        ("MD", "Maryland"),
        ("MA", "Massachusetts"),
        ("MI", "Michigan"),
        ("MN", "Minnesota"),
        ("MS", "Mississippi"),
        ("MO", "Missouri"),
        ("MT", "Montana"),
        ("NE", "Nebraska"),
        ("NV", "Nevada"),
        ("NH", "New Hampshire"),
        ("NJ", "New Jersey"),
        ("NM", "New Mexico"),
        ("NY", "New York"),
        ("NC", "North Carolina"),
        ("ND", "North Dakota"),
        ("OH", "Ohio"),
        ("OK", "Oklahoma"),
        ("OR", "Oregon"),
        ("PA", "Pennsylvania"),
        ("RI", "Rhode Island"),
        ("SC", "South Carolina"),
        ("SD", "South Dakota"),
        ("TN", "Tennessee"),
        ("TX", "Texas"),
        ("UT", "Utah"),
        ("VT", "Vermont"),
        ("VA", "Virginia"),
        ("WA", "Washington"),
        ("WV", "West Virginia"),
        ("WI", "Wisconsin"),
        ("WY", "Wyoming"),
    ]
    
    EVENT_TYPE_CHOICES = [
        ("Academic", "Academic"),
        ("Adventure", "Adventure"),
        ("Art", "Art"),
        ("Conference", "Conference"),
        ("Dance", "Dance"),
        ("Exhibition", "Exhibition"),
        ("Fashion", "Fashion"),
        ("Fundraiser", "Fundraiser"),
        ("Greek", "Greek"),
        ("Health", "Health"),
        ("Music", "Music"),
        ("Networking", "Networking"),
        ("Photography", "Photography"),
        ("Social", "Social"),
        ("Spiritual", "Spiritual"),
        ("Sports", "Sports"),
        ("Technology", "Technology"),
        ("Volunteer", "Volunteer"),
        ("Workshop", "Workshop"),
    ]
    
    event_type = forms.ChoiceField(
        label=_("Decide what type of experience this is"),
        choices=[("", "Select an option")] + EVENT_TYPE_CHOICES,
        required=True,
    )
    
    
    state = forms.ChoiceField(
        label=_("State"),
        choices=[("", "Select an option")] + STATE_CHOICES,
        required=True,
    )
    
    date = forms.DateField(
        label=_("Choose date"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )

    start_time = forms.TimeField(
        label=_("Start time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    end_time = forms.TimeField(
        label=_("End time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    class Meta:
        model = Event

        fields = [
            "title",
            "event_type",
            "date",
            "start_time",
            "end_time",
            "description",
            "hide_address",
            "couponsActivated",
            "country",
            "building_name",
            "street",
            "apt_suite_unit",
            "city",
            "state",
            "zip_code",
            "header_photo",
            "body_photo_one",
            "body_photo_two",
            "body_photo_three",
            "body_photo_four",
            "body_photo_five",
            "crew_discount",
            "minimum_crew_size",
            "crew_discount_percentage",
            "show_guest_list",
            "forAllDisplay",
            'forCollegesDisplay',
        ]

        widgets = {
            'address': forms.TextInput(attrs={
                'placeholder': 'Enter full address',
                'class': 'address-input'
            }),
            'building_name': forms.TextInput(attrs={
                'placeholder': 'Building name (optional)',
                'class': 'building-name-input'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Check if user is in a college
            is_in_college = hasattr(user, 'user_profile') and user.user_profile.college is not None
            self.fields['forCollegesDisplay'].disabled = not is_in_college
            if not is_in_college:
                self.fields['forCollegesDisplay'].help_text = _("You must be in a college to enable this option")
        

class EditEventForm(forms.ModelForm):
    AGE_RESTRICTION_CHOICES = [
        ("", "No Age Restriction"),
        ("18+", "18+"),
        ("21+", "21+"),
    ]

    age_restriction = forms.ChoiceField(
        label=_("Age Restriction"),
        required=False,
        choices=AGE_RESTRICTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'age-restriction-radio'}),
    )

    date = forms.DateField(
        label=_("Choose date"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )

    start_time = forms.TimeField(
        label=_("Start time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )

    end_time = forms.TimeField(
        label=_("End time"),
        required=False,
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        input_formats=["%H:%M"],
    )
    
    header_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    body_photo_one = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    body_photo_two = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    body_photo_three = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    body_photo_four = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )
    body_photo_five = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'custom-file-input'})
    )

    class Meta:
        model = Event
        fields = [
            "title",
            "event_type",
            "date",
            "start_time",
            "end_time",
            "description",
            "building_name",
            "street",
            "apt_suite_unit", 
            "city",
            "state",
            "zip_code",
            "header_photo",
            "body_photo_one",
            "body_photo_two",
            "body_photo_three",
            "body_photo_four",
            "body_photo_five",
            "age_restriction",
            "hide_address",
            "forAllDisplay",
            "forCollegesDisplay",
            "show_guest_list",
            "crew_discount",
            "minimum_crew_size",
            "crew_discount_percentage"
        ]

    def __init__(self, *args, **kwargs):
        # Extract partial flag before calling parent's __init__
        self.partial = kwargs.pop('partial', False)
        super().__init__(*args, **kwargs)
        
        # If this is a partial update, make all fields optional
        if self.partial:
            for field in self.fields.values():
                field.required = False
        
class HostProfileForm(forms.ModelForm):
    class Meta:
        model = HostProfile
        fields = [ "cashapp_id", "google_pay_id", "apple_pay_id"]
        
class CouponCodeForm(forms.ModelForm):
    discount_percentage = forms.IntegerField(
        min_value=1, 
        max_value=100,
        label=_("Discount Percentage"),
        widget=forms.NumberInput(attrs={"type": "number"})
    )
    expiration_date = forms.DateField(
        label=_("Choose expiration date"),
        required=False,
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        input_formats=["%Y-%m-%d"],
    )
        
    class Meta:
        model = CouponCode
        fields = ['code', 'discount_percentage', 'expiration_date']