from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Turf, Booking, Review, BlockedSlot, TurfImage, Sport, Amenity
from django.core.exceptions import ValidationError
from datetime import date as date_obj, time, datetime


class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=False)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES, initial='PLAYER')
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'role', 'password1', 'password2')


class TurfForm(forms.ModelForm):
    class Meta:
        model = Turf
        fields = ['name', 'location', 'google_map_link', 'image', 'opening_time', 'closing_time',
                  'base_price_per_hour', 'peak_hour_multiplier', 'weekend_multiplier', 'sports', 'amenities']
        widgets = {
            'opening_time': forms.TimeInput(attrs={'type': 'time'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time'}),
            'sports': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'amenities': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    image = forms.ImageField(required=False, help_text='Upload a primary image for the turf')


class TurfImageForm(forms.ModelForm):
    class Meta:
        model = TurfImage
        fields = ['image', 'is_primary']


class BookingForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'min': str(date_obj.today())}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    class Meta:
        model = Booking
        fields = ['sport', 'date', 'start_time', 'end_time']
    
    def __init__(self, *args, turf=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.turf = turf
        if turf:
            self.fields['sport'].queryset = turf.sports.all()
            self.fields['sport'].required = True
            self.fields['sport'].empty_label = "Choose the sport you are playing"
            self.fields['sport'].widget.attrs.update({'class': 'form-select'})
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if not all([booking_date, start_time, end_time]):
            return cleaned_data
        
        # Check if end time is after start time
        if end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        
        # Check if date is not in the past
        if booking_date < date_obj.today():
            raise ValidationError("Cannot book for past dates.")
        
        # Check if time is within turf operating hours
        if self.turf:
            if start_time < self.turf.opening_time or end_time > self.turf.closing_time:
                raise ValidationError(
                    f"Booking time must be between {self.turf.opening_time} and {self.turf.closing_time}"
                )
            
            # Check for overlaps
            if Booking.check_overlap(self.turf, booking_date, start_time, end_time):
                raise ValidationError("This time slot is already booked. Please choose another time.")
        
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class BlockedSlotForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    class Meta:
        model = BlockedSlot
        fields = ['date', 'start_time', 'end_time', 'reason']


class TurfSearchForm(forms.Form):
    location = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'placeholder': 'City'}))
    sport_type = forms.ModelChoiceField(
        queryset=Sport.objects.all(),
        required=False,
        empty_label='All Sports',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

