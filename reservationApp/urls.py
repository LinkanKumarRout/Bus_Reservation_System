from django.urls import path
from . import views

urlpatterns = [
    path('', views.homePage),
    path('home', views.homePage, name='home'),
    path('signup', views.signup_view, name='signup'),
    path('login', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('find-trips/', views.find_trips, name='find-trips'),
    path('book-trip/<int:schedule_id>/', views.book_trip, name='book-trip'),
    path('booking-confirmation/<int:booking_id>/', views.booking_confirmation, name='booking-confirmation'),
    path('contact-us/', views.contact_us, name='contact-us'),
    path('update-profile/', views.update_profile, name='update-profile'),
    path('all_schedules', views.schedule_list, name="schedule-list"),
    path('user/bookings/', views.user_bookings, name='user-bookings'),
    path('bus/categories', views.all_categories, name='all-categories'),
    path('buses/list', views.all_buses, name='all-buses'),
    path('locations/list', views.all_locations, name='all-locations'),
    path('booking/<int:booking_id>/payment/', views.payment_page, name='payment_page'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('cancel_booking/', views.cancel_booking, name='cancel_booking'),
    path('delete_booking/', views.delete_booking, name='delete_booking'),
]
