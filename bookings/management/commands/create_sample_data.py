from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
from bookings.models import CustomUser, Turf, Booking, Review, TurfImage


class Command(BaseCommand):
    help = 'Create sample data for TurfTime'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create admin user
        admin, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@turftime.com',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user (username: admin, password: admin123)'))
        
        # Create sample owners
        owners = []
        for i in range(3):
            owner, created = CustomUser.objects.get_or_create(
                username=f'owner{i+1}',
                defaults={
                    'email': f'owner{i+1}@example.com',
                    'role': 'OWNER',
                    'phone_number': f'987654321{i}',
                }
            )
            if created:
                owner.set_password('owner123')
                owner.save()
            owners.append(owner)
        
        # Create sample players
        players = []
        for i in range(5):
            player, created = CustomUser.objects.get_or_create(
                username=f'player{i+1}',
                defaults={
                    'email': f'player{i+1}@example.com',
                    'role': 'PLAYER',
                    'phone_number': f'987654322{i}',
                }
            )
            if created:
                player.set_password('player123')
                player.save()
            players.append(player)
        
        # Create sample turfs
        turf_data = [
            {
                'name': 'Green Field Sports Complex',
                'location': 'Mumbai',
                'sport_types': ['FOOTBALL'],
                'opening_time': time(6, 0),
                'closing_time': time(23, 0),
                'base_price_per_hour': 1500,
                'amenities': {'parking': True, 'water': True, 'lights': True, 'changing_room': True},
            },
            {
                'name': 'Cricket Arena',
                'location': 'Delhi',
                'sport_types': ['CRICKET'],
                'opening_time': time(7, 0),
                'closing_time': time(22, 0),
                'base_price_per_hour': 2000,
                'amenities': {'parking': True, 'water': True, 'lights': True},
            },
            {
                'name': 'Badminton Court Elite',
                'location': 'Bangalore',
                'sport_types': ['BADMINTON'],
                'opening_time': time(6, 0),
                'closing_time': time(23, 0),
                'base_price_per_hour': 800,
                'amenities': {'parking': True, 'water': True, 'lights': True, 'wifi': True},
            },
            {
                'name': 'Basketball Zone',
                'location': 'Mumbai',
                'sport_types': ['BASKETBALL'],
                'opening_time': time(8, 0),
                'closing_time': time(22, 0),
                'base_price_per_hour': 1200,
                'amenities': {'parking': True, 'water': True, 'lights': True, 'changing_room': True},
            },
            {
                'name': 'Tennis Club Premium',
                'location': 'Delhi',
                'sport_types': ['TENNIS'],
                'opening_time': time(6, 0),
                'closing_time': time(23, 0),
                'base_price_per_hour': 1800,
                'amenities': {'parking': True, 'water': True, 'lights': True, 'changing_room': True, 'wifi': True},
            },
        ]
        
        turfs = []
        for i, data in enumerate(turf_data):
            turf, created = Turf.objects.get_or_create(
                name=data['name'],
                defaults={
                    'location': data['location'],
                    'sport_types': data['sport_types'],
                    'opening_time': data['opening_time'],
                    'closing_time': data['closing_time'],
                    'base_price_per_hour': data['base_price_per_hour'],
                    'amenities': data['amenities'],
                    'owner': owners[i % len(owners)],
                    'is_approved': True,
                }
            )
            turfs.append(turf)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created turf: {turf.name}'))
        
        # Create sample bookings
        today = date.today()
        for i in range(10):
            turf = turfs[i % len(turfs)]
            player = players[i % len(players)]
            booking_date = today + timedelta(days=i % 7)
            start_hour = 10 + (i % 8)
            end_hour = start_hour + 2
            
            booking, created = Booking.objects.get_or_create(
                turf=turf,
                user=player,
                date=booking_date,
                start_time=time(start_hour, 0),
                end_time=time(end_hour, 0),
                defaults={
                    'total_price': turf.calculate_price(
                        time(start_hour, 0),
                        time(end_hour, 0),
                        booking_date
                    ),
                    'status': 'CONFIRMED' if i % 2 == 0 else 'PENDING',
                }
            )
            if created:
                booking.generate_qr_code()
                booking.save()
        
        # Create sample reviews
        for i, turf in enumerate(turfs[:3]):
            for j, player in enumerate(players[:3]):
                Review.objects.get_or_create(
                    turf=turf,
                    user=player,
                    defaults={
                        'rating': 4 + (i + j) % 2,
                        'comment': f'Great turf! Had an amazing time playing here.',
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('\nSample users:')
        self.stdout.write('  Admin: admin / admin123')
        self.stdout.write('  Owners: owner1, owner2, owner3 / owner123')
        self.stdout.write('  Players: player1, player2, player3, player4, player5 / player123')

