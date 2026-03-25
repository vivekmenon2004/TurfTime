import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'turftime_project.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_admin():
    User = get_user_model()
    username = 'admin'
    password = 'admin123'
    email = 'admin@turftime.com'
    
    try:
        if not User.objects.filter(username=username).exists():
            # Create superuser with ADMIN role
            user = User.objects.create_superuser(
                username=username, 
                email=email, 
                password=password
            )
            # Explicitly set role to ADMIN just in case (though is_superuser covers permissions, the app logic checks role)
            user.role = 'ADMIN'
            user.save()
            print(f"SUCCESS: Superuser '{username}' created with password '{password}'")
        else:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.role = 'ADMIN'
            user.is_superuser = True
            user.is_staff = True
            user.save()
            print(f"SUCCESS: Superuser '{username}' updated. Password reset to '{password}'")
            
    except Exception as e:
        print(f"ERROR: Failed to create/update superuser: {e}")

if __name__ == '__main__':
    create_admin()
