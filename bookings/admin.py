from django.contrib import admin # type: ignore
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # type: ignore
from .models import CustomUser, Turf, TurfImage, Booking, Review, BlockedSlot, AuditLog, Sport, Amenity # type: ignore

admin.site.register(Sport)
admin.site.register(Amenity)

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'phone_number', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'role')}),
    )


class TurfImageInline(admin.TabularInline):
    model = TurfImage
    extra = 1


@admin.register(Turf)
class TurfAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'get_sport_types_display', 'owner', 'base_price_per_hour', 'is_approved', 'is_active']
    list_filter = ['is_approved', 'is_active', 'location']
    search_fields = ['name', 'location', 'owner__username']
    inlines = [TurfImageInline]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'location', 'google_map_link', 'sports', 'owner')
        }),
        ('Timings', {
            'fields': ('opening_time', 'closing_time')
        }),
        ('Pricing', {
            'fields': ('base_price_per_hour', 'peak_hour_multiplier', 'weekend_multiplier')
        }),
        ('Amenities', {
            'fields': ('amenities',)
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'user', 'turf', 'date', 'start_time', 'end_time', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'date', 'turf', 'created_at']
    search_fields = ['user__username', 'turf__name', 'booking_id']
    readonly_fields = ['created_at', 'updated_at', 'qr_code']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Booking Details', {
            'fields': ('turf', 'user', 'date', 'start_time', 'end_time', 'total_price', 'status')
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'turf', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'turf__name', 'comment']


@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display = ['turf', 'date', 'start_time', 'end_time', 'reason', 'created_at']
    list_filter = ['date', 'turf']
    search_fields = ['turf__name', 'reason']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['booking', 'action', 'user', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['booking__booking_id', 'user__username']
    readonly_fields = ['created_at']
