from django.shortcuts import render, redirect, get_object_or_404 # type: ignore
from django.contrib.auth import login, logout # type: ignore
from django.contrib.auth.decorators import login_required, user_passes_test # type: ignore
from django.contrib import messages # type: ignore
from django.db.models import Q, Sum, Count, Avg # type: ignore
from django.utils import timezone # type: ignore
from django.http import JsonResponse, HttpResponse # type: ignore
from django.core.mail import send_mail # type: ignore
from django.conf import settings # type: ignore
from datetime import date as date_obj, datetime, timedelta # type: ignore
import requests # type: ignore
import json # type: ignore

from .models import CustomUser, Turf, Booking, Review, BlockedSlot, AuditLog, TurfImage # type: ignore
from .forms import ( # type: ignore
    CustomUserCreationForm, TurfForm, BookingForm, ReviewForm, 
    BlockedSlotForm, TurfSearchForm, TurfImageForm
)


def home(request):
    """Landing page"""
    # Get statistics
    stats = {
        'venues': Turf.objects.filter(is_approved=True, is_active=True).count(),
        'bookings': Booking.objects.filter(status__in=['CONFIRMED', 'COMPLETED']).count(),
        'satisfaction': Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    if stats['satisfaction']:
        stats['satisfaction'] = round(stats['satisfaction'] * 20, 0)  # Convert to percentage
    
    # Get featured turfs
    featured_turfs = Turf.objects.filter(is_approved=True, is_active=True)[:6]
    
    context = {
        'stats': stats,
        'featured_turfs': featured_turfs,
    }
    return render(request, 'bookings/home.html', context)


def register(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Registration successful.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'bookings/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate # type: ignore
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'bookings/login.html')


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    """Role-based dashboard"""
    user = request.user
    
    if user.is_player():
        return player_dashboard(request)
    elif user.is_owner():
        return owner_dashboard(request)
    elif user.is_admin():
        return admin_dashboard(request)
    else:
        return redirect('home')


def player_dashboard(request):
    """Player dashboard"""
    user = request.user
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')

    upcoming_bookings = Booking.objects.filter(
        user=user,
        date__gte=date_obj.today(),
        status__in=['PENDING', 'CONFIRMED'],
        payment_status='PAID'
    ).order_by('-created_at')

    # All bookings for this user — shows full history (confirmed, cancelled, completed, etc.)
    past_bookings = Booking.objects.filter(
        user=user
    ).order_by('-created_at')

    if status_filter:
        upcoming_bookings = upcoming_bookings.filter(status=status_filter)
        past_bookings = past_bookings.filter(status=status_filter)
    if date_filter:
        upcoming_bookings = upcoming_bookings.filter(date=date_filter)
        past_bookings = past_bookings.filter(date=date_filter)

    context = {
        'upcoming_bookings': upcoming_bookings,
        'past_bookings': past_bookings,
        'current_status': status_filter,
        'current_date': date_filter,
    }
    return render(request, 'bookings/player_dashboard.html', context)


def owner_dashboard(request):
    """Turf owner dashboard"""
    user = request.user
    turfs = Turf.objects.filter(owner=user)
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')

    # Get ALL bookings for owner's turfs (all statuses), newest first
    bookings = Booking.objects.filter(turf__owner=user).order_by('-created_at')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(date=date_filter)

    # Calculate earnings (always unfiltered)
    total_earnings = Booking.objects.filter(
        turf__owner=user,
        status__in=['CONFIRMED', 'COMPLETED'],
        payment_status='PAID'
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Monthly earnings
    current_month = timezone.now().month
    monthly_earnings = Booking.objects.filter(
        turf__owner=user,
        status__in=['CONFIRMED', 'COMPLETED'],
        payment_status='PAID',
        date__month=current_month
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Pending bookings count
    pending_count = Booking.objects.filter(
        turf__owner=user,
        status='PENDING',
        payment_status='PAID'
    ).count()

    context = {
        'turfs': turfs,
        'bookings': bookings,
        'total_earnings': total_earnings,
        'monthly_earnings': monthly_earnings,
        'pending_count': pending_count,
        'current_status': status_filter,
        'current_date': date_filter,
    }
    return render(request, 'bookings/owner_dashboard.html', context)


@user_passes_test(lambda u: u.is_admin())
def admin_dashboard(request):
    """Admin dashboard"""
    # Pending turf approvals
    pending_turfs_count = Turf.objects.filter(is_approved=False).count()
    pending_turfs_list = Turf.objects.filter(is_approved=False)
    
    # Total users
    total_users = CustomUser.objects.count()
    total_players = CustomUser.objects.filter(role='PLAYER').count()
    total_owners = CustomUser.objects.filter(role='OWNER').count()
    
    # All bookings with filter support — no limit, newest first
    recent_bookings = Booking.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    if status_filter:
        recent_bookings = recent_bookings.filter(status=status_filter)
    if date_filter:
        recent_bookings = recent_bookings.filter(date=date_filter)
    
    # Total revenue
    total_revenue = Booking.objects.filter(
        status__in=['CONFIRMED', 'COMPLETED'],
        payment_status='PAID'
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Chart Data
    # Revenue by Turf (Top 5)
    turf_revenue = Turf.objects.annotate(
        revenue=Sum('bookings__total_price', filter=Q(bookings__status__in=['CONFIRMED', 'COMPLETED'], bookings__payment_status='PAID'))
    ).order_by('-revenue')[:5]
    
    sport_counts = list(Booking.objects.values('sport__name').annotate(count=Count('sport')))
    
    context = {
        'pending_turfs': pending_turfs_count,
        'pending_turfs_list': pending_turfs_list,
        'total_users': total_users,
        'total_players': total_players,
        'total_owners': total_owners,
        'recent_bookings': recent_bookings,
        'total_revenue': total_revenue,
        'current_status': status_filter,
        'current_date': date_filter,
        'revenue_labels': json.dumps([t.name for t in turf_revenue]),
        'revenue_data': json.dumps([float(t.revenue or 0) for t in turf_revenue]),
        'sport_labels': json.dumps([item['sport__name'] or 'Unknown' for item in sport_counts]),
        'sport_data': json.dumps([item['count'] for item in sport_counts]),
    }
    return render(request, 'bookings/admin_dashboard.html', context)


def search_turfs(request):
    """Search turfs by location and sport"""
    form = TurfSearchForm(request.GET)
    turfs = Turf.objects.filter(is_approved=True, is_active=True)
    
    if form.is_valid():
        location = form.cleaned_data.get('location')
        sport_type = form.cleaned_data.get('sport_type')

        if location:
            turfs = turfs.filter(location__icontains=location)
        if sport_type:
            turfs = turfs.filter(sports=sport_type)
    
    context = {
        'form': form,
        'turfs': turfs,
    }
    return render(request, 'bookings/search_turfs.html', context)


def turf_detail(request, turf_id):
    """Turf detail page with availability calendar"""
    turf = get_object_or_404(Turf, turf_id=turf_id, is_approved=True, is_active=True)
    
    # Get reviews
    reviews = Review.objects.filter(turf=turf).order_by('-created_at')[:10]
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Get bookings for the next 7 days
    start_date = date_obj.today()
    end_date = start_date + timedelta(days=7)
    
    bookings = Booking.objects.filter(
        turf=turf,
        date__gte=start_date,
        date__lte=end_date,
        status__in=['PENDING', 'CONFIRMED']
    ).order_by('date', 'start_time')
    
    # Get blocked slots
    blocked_slots = BlockedSlot.objects.filter(
        turf=turf,
        date__gte=start_date,
        date__lte=end_date
    )
    
    # Check if user can review
    can_review = False
    if request.user.is_authenticated:
        has_booking = Booking.objects.filter(
            turf=turf,
            user=request.user,
            status__in=['CONFIRMED', 'COMPLETED']
        ).exists()
        has_review = Review.objects.filter(turf=turf, user=request.user).exists()
        can_review = has_booking and not has_review
    
    # Weather API (optional)
    weather_warning = None
    sports_list = [s.name.upper() for s in turf.sports.all()]
    if hasattr(settings, 'WEATHER_API_KEY') and settings.WEATHER_API_KEY and any(s in ['FOOTBALL', 'CRICKET', 'TENNIS'] for s in sports_list):
        try:
            # This is a placeholder - implement actual weather API call
            pass
        except:
            pass
    
    context = {
        'turf': turf,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'bookings': bookings,
        'blocked_slots': blocked_slots,
        'can_review': can_review,
        'weather_warning': weather_warning,
    }
    return render(request, 'bookings/turf_detail.html', context)


@login_required
def book_turf(request, turf_id):
    """Book a turf slot"""
    turf = get_object_or_404(Turf, turf_id=turf_id, is_approved=True, is_active=True)
    
    if request.method == 'POST':
        # Eradicate any previous abandoned checkout sessions for this user to keep DB pristine
        Booking.objects.filter(user=request.user, payment_status='PENDING').delete()
        
        form = BookingForm(request.POST, turf=turf)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.turf = turf
            booking.user = request.user
            
            # Calculate price
            booking.total_price = turf.calculate_price(
                booking.start_time,
                booking.end_time,
                booking.date
            )
            
            booking.save()
            
            # Generate QR code
            booking.generate_qr_code()
            booking.save()
            
            # Create audit log
            AuditLog.objects.create(
                booking=booking,
                action='CREATED',
                user=request.user,
                details={'total_price': str(booking.total_price), 'sport': booking.sport.name if booking.sport else 'N/A'}
            )
            
            # Send email notification
            try:
                send_booking_confirmation_email(booking)
            except:
                pass  # Email sending is optional
            
            messages.success(request, f'Booking initiated! Proceed to payment. Total: ₹{booking.total_price}')
            return redirect('payment', booking_id=booking.booking_id)
    else:
        form = BookingForm(turf=turf)
    
    context = {
        'turf': turf,
        'form': form,
    }
    return render(request, 'bookings/book_turf.html', context)


@login_required
def payment(request, booking_id):
    """Fake payment page"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    if booking.payment_status == 'PAID':
        return redirect('booking_detail', booking_id=booking.booking_id)
    
    if request.method == 'POST':
        # Simulate payment processing
        import time
        # time.sleep(1) # We don't want to block the thread in a real app, but this is a fake payment
        
        booking.payment_status = 'PAID'
        booking.status = 'CONFIRMED'  # Auto-confirm after payment for this demo
        booking.save()
        
        # Update audit log
        AuditLog.objects.create(
            booking=booking,
            action='CONFIRMED',
            user=request.user,
            details={'payment': 'SUCCESS'}
        )
        
        messages.success(request, 'Payment successful! Here is your booking details and QR code.')
        return redirect('booking_detail', booking_id=booking.booking_id)
        
    context = {
        'booking': booking,
    }
    return render(request, 'bookings/payment.html', context)


@login_required
def booking_detail(request, booking_id):
    """View booking details"""
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check if user has permission
    if not (booking.user == request.user or booking.turf.owner == request.user or request.user.is_admin()):
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('dashboard')
    
    # Check if the booking is in the past
    booking_datetime = datetime.combine(booking.date, booking.start_time)
    is_past = booking_datetime < datetime.now()
    
    context = {
        'booking': booking,
        'is_past': is_past,
    }
    return render(request, 'bookings/booking_detail.html', context)


@login_required
def my_bookings(request):
    """View all bookings for a player"""
    bookings = Booking.objects.filter(user=request.user, payment_status='PAID').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(date=date_filter)
    context = {
        'bookings': bookings,
        'current_status': status_filter,
        'current_date': date_filter,
    }
    return render(request, 'bookings/my_bookings.html', context)


@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, booking_id=booking_id)
    is_owner = (booking.turf.owner == request.user)
    
    if booking.user != request.user and not is_owner:
        messages.error(request, 'You can only cancel your own bookings or bookings for your turf.')
        return redirect('dashboard')
    
    if booking.status in ['CANCELLED', 'COMPLETED']:
        messages.error(request, 'This booking cannot be cancelled.')
        return redirect('booking_detail', booking_id=booking_id)
        
    booking_datetime = datetime.combine(booking.date, booking.start_time)
    if booking_datetime < datetime.now():
        messages.error(request, 'This booking has already passed and cannot be cancelled or rejected.')
        return redirect('booking_detail', booking_id=booking_id)
    
    if request.method == 'POST':
        booking.status = 'CANCELLED'
        booking.save()
        reason = request.POST.get('reason', 'None provided')
        detail_msg = f'Owner rejected: {reason}' if is_owner else 'User cancelled'
        
        # Create audit log
        AuditLog.objects.create(
            booking=booking,
            action='CANCELLED',
            user=request.user,
            details={'reason': detail_msg}
        )
        
        messages.success(request, 'Booking successfully cancelled/rejected.')
        return redirect('booking_detail', booking_id=booking_id)
    
    return render(request, 'bookings/cancel_booking.html', {'booking': booking, 'is_owner': is_owner})


@login_required
def cancel_checkout(request, booking_id):
    """If user cancels directly from the payment page, destroy the unfinished booking record completely."""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user, payment_status='PENDING')
    booking.delete()
    messages.success(request, 'Checkout cancelled safely. No booking was created.')
    return redirect('search_turfs')


@login_required
@user_passes_test(lambda u: u.is_owner())
def add_turf(request):
    """Add a new turf (owner)"""
    if request.method == 'POST':
        form = TurfForm(request.POST, request.FILES)
        if form.is_valid():
            turf = form.save(commit=False)
            turf.owner = request.user
            turf.save()
            form.save_m2m()  # This saves the many-to-many fields like sports and amenities
            
            image = form.cleaned_data.get('image')
            if image:
                TurfImage.objects.create(turf=turf, image=image, is_primary=True)
                
            messages.success(request, 'Turf added successfully! Waiting for admin approval.')
            return redirect('my_turfs')
    else:
        form = TurfForm()
    
    return render(request, 'bookings/add_turf.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_owner())
def my_turfs(request):
    """List owner's turfs"""
    turfs = Turf.objects.filter(owner=request.user)
    return render(request, 'bookings/my_turfs.html', {'turfs': turfs})


@login_required
@user_passes_test(lambda u: u.is_owner())
def edit_turf(request, turf_id):
    """Edit turf details"""
    turf = get_object_or_404(Turf, turf_id=turf_id, owner=request.user)
    
    if request.method == 'POST':
        form = TurfForm(request.POST, request.FILES, instance=turf)
        if form.is_valid():
            turf = form.save(commit=False)
            turf.save()
            form.save_m2m()

            image = form.cleaned_data.get('image')
            if image:
                # Unset previous primary image
                TurfImage.objects.filter(turf=turf, is_primary=True).update(is_primary=False)
                TurfImage.objects.create(turf=turf, image=image, is_primary=True)

            messages.success(request, 'Turf updated successfully!')
            return redirect('turf_detail', turf_id=turf.turf_id)
    else:
        form = TurfForm(instance=turf)
    
    return render(request, 'bookings/edit_turf.html', {'form': form, 'turf': turf})


@login_required
@user_passes_test(lambda u: u.is_owner())
def manage_bookings(request, turf_id):
    """Manage bookings for a turf (owner)"""
    turf = get_object_or_404(Turf, turf_id=turf_id, owner=request.user)
    bookings = Booking.objects.filter(turf=turf, payment_status='PAID').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if date_filter:
        bookings = bookings.filter(date=date_filter)
    return render(request, 'bookings/manage_bookings.html', {
        'turf': turf,
        'bookings': bookings,
        'current_status': status_filter,
        'current_date': date_filter,
    })


@login_required
@user_passes_test(lambda u: u.is_owner())
def confirm_booking(request, booking_id):
    """Confirm a booking (owner)"""
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    if booking.turf.owner != request.user:
        messages.error(request, 'You do not have permission to confirm this booking.')
        return redirect('dashboard')
    
    if booking.status != 'PENDING':
        messages.error(request, 'This booking cannot be confirmed.')
        return redirect('booking_detail', booking_id=booking_id)
    
    booking.status = 'CONFIRMED'
    booking.save()
    
    # Create audit log
    AuditLog.objects.create(
        booking=booking,
        action='CONFIRMED',
        user=request.user,
        details={}
    )
    
    # Send email
    try:
        send_booking_confirmation_email(booking)
    except:
        pass
    
    messages.success(request, 'Booking confirmed successfully!')
    return redirect('booking_detail', booking_id=booking_id)


@login_required
@user_passes_test(lambda u: u.is_owner())
def block_slot(request, turf_id):
    """Block a slot manually (owner)"""
    turf = get_object_or_404(Turf, turf_id=turf_id, owner=request.user)
    
    if request.method == 'POST':
        form = BlockedSlotForm(request.POST)
        if form.is_valid():
            blocked = form.save(commit=False)
            blocked.turf = turf
            blocked.save()
            messages.success(request, 'Slot blocked successfully!')
            return redirect('turf_detail', turf_id=turf.turf_id)
    else:
        form = BlockedSlotForm()
    
    return render(request, 'bookings/block_slot.html', {'form': form, 'turf': turf})


@login_required
@user_passes_test(lambda u: u.is_admin())
def approve_turf(request, turf_id):
    """Approve a turf (admin)"""
    turf = get_object_or_404(Turf, turf_id=turf_id)
    
    if request.method == 'POST':
        turf.is_approved = True
        turf.save()
        messages.success(request, f'{turf.name} has been approved!')
        return redirect('dashboard')
    
    return render(request, 'bookings/approve_turf.html', {'turf': turf})


@login_required
def add_review(request, turf_id):
    """Add a review for a turf"""
    turf = get_object_or_404(Turf, turf_id=turf_id)
    
    # Check if user has booked this turf
    has_booking = Booking.objects.filter(
        turf=turf,
        user=request.user,
        status__in=['CONFIRMED', 'COMPLETED']
    ).exists()
    
    if not has_booking:
        messages.error(request, 'You must have a confirmed booking to review this turf.')
        return redirect('turf_detail', turf_id=turf_id)
    
    # Check if already reviewed
    if Review.objects.filter(turf=turf, user=request.user).exists():
        messages.error(request, 'You have already reviewed this turf.')
        return redirect('turf_detail', turf_id=turf_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.turf = turf
            review.user = request.user
            review.save()
            messages.success(request, 'Review added successfully!')
            return redirect('turf_detail', turf_id=turf_id)
    else:
        form = ReviewForm()
    
    return render(request, 'bookings/add_review.html', {'form': form, 'turf': turf})


def get_available_slots(request, turf_id):
    """API endpoint to get available slots for a date"""
    turf = get_object_or_404(Turf, turf_id=turf_id)
    selected_date = request.GET.get('date')
    
    if not selected_date:
        return JsonResponse({'error': 'Date required'}, status=400)
    
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # Get bookings for the date
    bookings = Booking.objects.filter(
        turf=turf,
        date=selected_date,
        status__in=['PENDING', 'CONFIRMED'],
        payment_status='PAID'
    )
    
    # Get blocked slots
    blocked = BlockedSlot.objects.filter(turf=turf, date=selected_date)
    
    # Generate available slots (hourly)
    slots = []
    current_time = turf.opening_time
    while current_time < turf.closing_time:
        slot_start = current_time
        slot_end = (datetime.combine(date_obj.today(), slot_start) + timedelta(hours=1)).time()
        
        if slot_end > turf.closing_time:
            slot_end = turf.closing_time
        
        # Check if slot is available
        is_booked = bookings.filter(
            start_time__lt=slot_end,
            end_time__gt=slot_start
        ).exists()
        
        is_blocked = blocked.filter(
            start_time__lt=slot_end,
            end_time__gt=slot_start
        ).exists()
        
        slots.append({
            'start': slot_start.strftime('%H:%M'),
            'end': slot_end.strftime('%H:%M'),
            'available': not (is_booked or is_blocked),
            'is_booked': bool(is_booked),
            'is_blocked': bool(is_blocked),
        })
        
        current_time = slot_end
    
    return JsonResponse({'slots': slots})


def send_booking_confirmation_email(booking):
    """Send booking confirmation email"""
    subject = f'Booking Confirmation - {booking.turf.name}'
    message = f"""
    Hello {booking.user.username},
    
    Your booking has been confirmed!
    
    Turf: {booking.turf.name}
    Date: {booking.date}
    Time: {booking.start_time} - {booking.end_time}
    Total Price: ₹{booking.total_price}
    Status: {booking.get_status_display()}
    
    Thank you for using TurfTime!
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        fail_silently=True,
    )


@login_required
@user_passes_test(lambda u: u.is_admin())
def user_list(request):
    """List all users with filtering"""
    role_filter = request.GET.get('role')
    users = CustomUser.objects.all().order_by('-date_joined')
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    context = {
        'users': users,
        'current_role': role_filter,
    }
    return render(request, 'bookings/admin_user_list.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin())
def revenue_report(request):
    """Detailed revenue report"""
    # Revenue by Turf
    turf_revenue = Turf.objects.annotate(
        revenue=Sum('bookings__total_price', filter=Q(bookings__status__in=['CONFIRMED', 'COMPLETED'], bookings__payment_status='PAID')),
        booking_count=Count('bookings', filter=Q(bookings__status__in=['CONFIRMED', 'COMPLETED'], bookings__payment_status='PAID'))
    ).order_by('-revenue')
    
    # Recent Transactions
    transactions = Booking.objects.filter(
        status__in=['CONFIRMED', 'COMPLETED'],
        payment_status='PAID'
    ).order_by('-updated_at')[:50]
    
    total_revenue = transactions.aggregate(total=Sum('total_price'))['total'] or 0
    
    context = {
        'turf_revenue': turf_revenue,
        'transactions': transactions,
        'total_revenue': total_revenue
    }
    return render(request, 'bookings/admin_revenue.html', context)


@login_required
@user_passes_test(lambda u: u.is_admin())
def download_excel(request):
    """Download full bookings as Excel (CSV format)"""
    import csv
    from django.http import HttpResponse # type: ignore
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bookings_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Booking ID', 'User', 'Turf', 'Sport', 'Date', 'Time', 'Price', 'Status'])
    
    bookings = Booking.objects.all().order_by('-created_at')
    for b in bookings:
        sport_name = b.sport.name if b.sport else 'N/A'
        writer.writerow([
            b.booking_id,
            b.user.username,
            b.turf.name,
            sport_name,
            str(b.date),
            f"{b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')}",
            b.total_price,
            b.get_status_display()
        ])
    return response


@login_required
@user_passes_test(lambda u: u.is_admin())
def download_pdf(request):
    """Download full bookings as PDF using xhtml2pdf"""
    try:
        from xhtml2pdf import pisa # type: ignore
    except ImportError:
        messages.error(request, 'PDF generation library (xhtml2pdf) is not installed.')
        return redirect('dashboard')
        
    import io
    from django.http import HttpResponse # type: ignore
    from django.template.loader import get_template # type: ignore
    
    bookings = Booking.objects.all().order_by('-created_at')
    context = {'bookings': bookings}
    
    template = get_template('bookings/pdf_report.html')
    html = template.render(context)
    
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("utf-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="bookings_report.pdf"'
        return response
    
    messages.error(request, 'Error generating PDF')
    return redirect('dashboard')
