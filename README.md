# TurfTime - Sports Venue Booking System

A production-ready Django web application for booking sports venues (turfs). TurfTime connects players with real-time availability and empowers turf owners with seamless scheduling.

## Features

### For Players
- User registration and authentication
- Search turfs by city and sport type
- View detailed turf information with images
- Real-time slot availability
- Book time slots with automatic price calculation
- View booking history and upcoming bookings
- Receive booking confirmation with QR code
- Review and rate turfs

### For Turf Owners
- Register and manage multiple turfs
- Set pricing (base, peak hours, weekends)
- View and manage bookings
- Manually block slots for offline bookings
- Track earnings and revenue
- Upload multiple images per turf

### For Admins
- Approve/reject turf registrations
- Manage users and bookings
- View system-wide statistics
- Handle disputes

## Tech Stack

- **Backend**: Django 5.0+ (LTS)
- **Frontend**: Django Templates + Bootstrap 5
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: Django Auth with Custom User Model
- **Timezone**: Asia/Kolkata
- **Additional**: QR Code generation, Email notifications

## Installation

### Prerequisites

- Python 3.8+
- pip
- PostgreSQL (for production) or SQLite (for development)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Turftime
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** (optional)
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   USE_POSTGRES=False
   DB_NAME=db.sqlite3
   WEATHER_API_KEY=your-weather-api-key (optional)
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Create sample data** (optional)
   ```bash
   python manage.py create_sample_data
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Home: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Sample Users

After running `create_sample_data`:

- **Admin**: username: `admin`, password: `admin123`
- **Owners**: username: `owner1`, `owner2`, `owner3`, password: `owner123`
- **Players**: username: `player1` to `player5`, password: `player123`

## Project Structure

```
Turftime/
├── bookings/              # Main app
│   ├── models.py         # CustomUser, Turf, Booking, Review models
│   ├── views.py          # All views (player, owner, admin)
│   ├── forms.py          # Django forms
│   ├── urls.py           # URL routing
│   ├── admin.py          # Admin configuration
│   └── management/       # Management commands
├── turftime_project/     # Project settings
│   ├── settings.py       # Django settings
│   └── urls.py           # Main URL config
├── templates/            # HTML templates
│   └── bookings/         # App templates
├── static/              # Static files (CSS, JS, images)
├── media/               # User uploaded files
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Core Features Explained

### Slot Overlap Prevention

The system prevents double-booking using a robust overlap detection algorithm:

```python
# A booking overlaps if:
existing.start_time < new.end_time AND
existing.end_time > new.start_time
```

This is implemented in the `Booking.check_overlap()` method and validated in the `BookingForm.clean()` method.

### Pricing Logic

- **Base Price**: Set per hour by turf owner
- **Peak Hours (6 PM - 10 PM)**: Multiplier applied (default 1.5x)
- **Weekends**: Additional multiplier (default 1.2x)
- **Combined**: Peak hours on weekends get both multipliers

Example: Base ₹1000/hour, peak 1.5x, weekend 1.2x
- Regular weekday: ₹1000/hour
- Peak weekday: ₹1500/hour
- Regular weekend: ₹1200/hour
- Peak weekend: ₹1800/hour

### QR Code Generation

Each confirmed booking automatically generates a QR code containing:
- Booking ID
- Turf name
- Date and time
- Stored in `media/qr_codes/`

### Email Notifications

Booking confirmations are sent via email (console backend in development). Configure SMTP in production:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-password'
```

## Database Models

### CustomUser
- Extends Django's AbstractUser
- Fields: `phone_number`, `role` (PLAYER, OWNER, ADMIN)

### Turf
- Fields: `name`, `location`, `sport_type`, `opening_time`, `closing_time`, `owner`, `amenities` (JSON), `base_price_per_hour`, `is_approved`

### Booking
- Fields: `turf`, `user`, `date`, `start_time`, `end_time`, `total_price`, `status`, `qr_code`
- Status: PENDING, CONFIRMED, CANCELLED, COMPLETED

### Review
- Fields: `turf`, `user`, `rating` (1-5), `comment`
- One review per user per turf

## Production Deployment

1. **Set DEBUG = False** in settings.py
2. **Configure PostgreSQL**:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'turftime_db',
           'USER': 'your_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```
3. **Collect static files**:
   ```bash
   python manage.py collectstatic
   ```
4. **Use a production WSGI server** (e.g., Gunicorn)
5. **Configure reverse proxy** (e.g., Nginx)
6. **Set up SSL/HTTPS**
7. **Configure proper email backend**

## API Endpoints

- `GET /api/slots/<turf_id>/?date=YYYY-MM-DD` - Get available slots for a date

## Security Considerations

- CSRF protection enabled
- Password validation
- SQL injection protection (Django ORM)
- XSS protection (Django templates)
- File upload validation
- Role-based access control

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on the repository.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

