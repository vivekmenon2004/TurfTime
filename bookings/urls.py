from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('search/', views.search_turfs, name='search_turfs'),
    path('contact/', views.home, name='contact'),
    path('turf/<int:turf_id>/', views.turf_detail, name='turf_detail'),
    
    # Player views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('book/<int:turf_id>/', views.book_turf, name='book_turf'),
    path('payment/<int:booking_id>/', views.payment, name='payment'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('cancel-checkout/<int:booking_id>/', views.cancel_checkout, name='cancel_checkout'),
    path('review/<int:turf_id>/', views.add_review, name='add_review'),
    
    # Owner views
    path('add-turf/', views.add_turf, name='add_turf'),
    path('my-turfs/', views.my_turfs, name='my_turfs'),
    path('edit-turf/<int:turf_id>/', views.edit_turf, name='edit_turf'),
    path('manage-bookings/<int:turf_id>/', views.manage_bookings, name='manage_bookings'),
    path('confirm-booking/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('block-slot/<int:turf_id>/', views.block_slot, name='block_slot'),
    
    # Admin views
    path('approve-turf/<int:turf_id>/', views.approve_turf, name='approve_turf'),
    path('management/users/', views.user_list, name='user_list'),
    path('management/revenue/', views.revenue_report, name='revenue_report'),
    path('management/download-excel/', views.download_excel, name='download_excel'),
    path('management/download-pdf/', views.download_pdf, name='download_pdf'),
    
    # API endpoints
    path('api/slots/<int:turf_id>/', views.get_available_slots, name='get_available_slots'),
]

