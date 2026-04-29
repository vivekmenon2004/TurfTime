from django.db import models # type: ignore
from django.contrib.auth.models import AbstractUser # type: ignore
from django.core.validators import MinValueValidator, MaxValueValidator # type: ignore
from django.utils import timezone # type: ignore
from datetime import datetime, time # type: ignore
import qrcode # type: ignore
from io import BytesIO # type: ignore
from django.core.files.base import ContentFile # type: ignore
import PIL # type: ignore


class CustomUser(AbstractUser):
    player_id = models.BigAutoField(primary_key=True)
    """
    Extended User model with phone number and role
    """
    ROLE_CHOICES = [
        ('PLAYER', 'Player'),
        ('OWNER', 'Turf Owner'),
        ('ADMIN', 'Super Admin'),
    ]
    
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='PLAYER')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_player(self):
        return self.role == 'PLAYER'
    
    def is_owner(self):
        return self.role == 'OWNER'
    
    def is_admin(self):
        return self.role == 'ADMIN' or self.is_superuser


class Sport(models.Model):
    """
    Sport types available
    """
    sport_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Amenity(models.Model):
    """
    Amenities available at turfs
    """
    amenity_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Amenities"
        
    def __str__(self):
        return self.name


class Turf(models.Model):
    """
    Sports venue model
    """
    turf_id = models.BigAutoField(primary_key=True)
    
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)  # City
    google_map_link = models.URLField(max_length=500, blank=True, help_text="Google Maps link to the turf location")
    
    sports = models.ManyToManyField(Sport, related_name='turfs', blank=True)
    amenities = models.ManyToManyField(Amenity, related_name='turfs', blank=True)
    
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_turfs')
    base_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    peak_hour_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.5, help_text="Multiplier for peak hours (6 PM - 10 PM)")
    weekend_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.2, help_text="Multiplier for weekends")
    is_approved = models.BooleanField(default=False, help_text="Admin approval required")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Turfs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.location}"
    
    def get_amenities_list(self):
        """Return amenities as a list"""
        return [a.name for a in self.amenities.all()]

    def get_sport_types_display(self):
        """Return comma-separated sport names for display"""
        return ', '.join(s.name for s in self.sports.all())

    get_sport_types_display.short_description = 'Sport Types' # type: ignore
    
    def calculate_price(self, start_time, end_time, date):
        """
        Calculate total price based on:
        - Base price per hour
        - Peak hours (6 PM - 10 PM) multiplier
        - Weekend multiplier
        """
        from datetime import timedelta
        
        # Calculate duration in hours
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, '%H:%M').time()
        if isinstance(end_time, str):
            end_time = datetime.strptime(end_time, '%H:%M').time()
        
        start_datetime = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)
        duration = (end_datetime - start_datetime).total_seconds() / 3600
        
        # Base price
        base_price = float(self.base_price_per_hour) * duration
        
        # Check if weekend
        is_weekend = date.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        # Calculate peak hours exact overlap
        peak_start = time(18, 0)  # 6 PM
        peak_end = time(22, 0)    # 10 PM
        
        peak_start_datetime = datetime.combine(date, peak_start)
        peak_end_datetime = datetime.combine(date, peak_end)
        
        # Find overlap
        overlap_start = max(start_datetime, peak_start_datetime)
        overlap_end = min(end_datetime, peak_end_datetime)
        
        peak_hours = 0
        if overlap_start < overlap_end:
            peak_hours = (overlap_end - overlap_start).total_seconds() / 3600
        
        if peak_hours > 0:
            regular_hours = duration - peak_hours
            regular_price = float(self.base_price_per_hour) * regular_hours
            peak_price = float(self.base_price_per_hour) * float(self.peak_hour_multiplier) * peak_hours
            
            if is_weekend:
                regular_price *= float(self.weekend_multiplier)
                peak_price *= float(self.weekend_multiplier)
            
            total_price = regular_price + peak_price
        else:
            total_price = base_price * (float(self.weekend_multiplier) if is_weekend else 1.0)
        
        return round(total_price, 2) # type: ignore


class TurfImage(models.Model):
    """
    Multiple images for a turf
    """
    image_id = models.BigAutoField(primary_key=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='turf_images/')
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', '-uploaded_at']
    
    def __str__(self):
        return f"Image for {self.turf.name}"


class Booking(models.Model):
    """
    Booking model with slot overlap prevention
    """
    booking_id = models.BigAutoField(primary_key=True)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]
    
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings')
    sport = models.ForeignKey(Sport, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['turf', 'date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.turf.name} on {self.date}"
    
    def generate_qr_code(self):
        """Generate QR code for booking"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"Booking ID: {self.booking_id}\nTurf: {self.turf.name}\nSport: {self.sport.name if self.sport else 'N/A'}\nDate: {self.date}\nTime: {self.start_time} - {self.end_time}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f'booking_{self.booking_id}_qr.png'
        self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
    
    def save(self, *args, **kwargs):
        if not self.qr_code and self.pk:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    @staticmethod
    def check_overlap(turf, date, start_time, end_time, exclude_booking_id=None):
        """
        Check if a booking overlaps with existing bookings
        Returns True if overlap exists, False otherwise
        """
        overlapping = Booking.objects.filter(
            turf=turf,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status__in=['PENDING', 'CONFIRMED'],
            payment_status='PAID'
        )
        
        if exclude_booking_id:
            overlapping = overlapping.exclude(booking_id=exclude_booking_id)
        
        return overlapping.exists()


class Review(models.Model):
    """
    Review and rating for turfs
    """
    review_id = models.BigAutoField(primary_key=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['turf', 'user']  # One review per user per turf
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.turf.name} ({self.rating} stars)"


class BlockedSlot(models.Model):
    """
    Manually blocked slots by turf owners for offline bookings
    """
    slot_id = models.BigAutoField(primary_key=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE, related_name='blocked_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.turf.name} - {self.date} {self.start_time} to {self.end_time}"


class AuditLog(models.Model):
    """
    Audit log for booking changes
    """
    log_id = models.BigAutoField(primary_key=True)
    
    ACTION_CHOICES = [
        ('CREATED', 'Created'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('UPDATED', 'Updated'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} - {self.booking} by {self.user}"
