import os
import django
from datetime import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'turftime_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from bookings.models import Turf

def create_test_data():
    User = get_user_model()
    
    # Create Owner
    owner_email = 'owner@example.com'
    owner_username = 'owner_test'
    if not User.objects.filter(username=owner_username).exists():
        owner = User.objects.create_user(
            username=owner_username,
            email=owner_email,
            password='password123',
            role='OWNER'
        )
        print(f"Created Owner: {owner_username}")
    else:
        owner = User.objects.get(username=owner_username)
        print(f"Owner {owner_username} exists")

    # Create Pending Turf
    turf_name = "Super Soccer Arena"
    if not Turf.objects.filter(name=turf_name).exists():
        Turf.objects.create(
            name=turf_name,
            location="Downtown Sports Complex",
            sport_types=['FOOTBALL', 'CRICKET'],
            opening_time=time(9, 0),
            closing_time=time(22, 0),
            owner=owner,
            base_price_per_hour=1500.00,
            is_approved=False,  # PENDING APPROVAL
            is_active=True
        )
        print(f"Created Pending Turf: '{turf_name}' - Validating Admin Approval Workflow")
    else:
        t = Turf.objects.get(name=turf_name)
        t.is_approved = False
        t.save()
        print(f"Reset Turf '{turf_name}' to Pending status")

if __name__ == '__main__':
    create_test_data()
