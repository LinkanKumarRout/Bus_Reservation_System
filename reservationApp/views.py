import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from .models import *
from .utils.email_utils import send_booking_confirmation
import paypalrestsdk
from django.conf import settings
from decimal import Decimal
import logging

# Home Page View
def homePage(request):
    return render(request, "reserve/index.html")

# Function for validating password
def validate_password(password1, password2):
    if password1 != password2:
        raise ValidationError('Passwords do not match')

    if len(password1) < 8:
        raise ValidationError('Password must be at least 8 characters long')

    if not re.search(r'[A-Z]', password1):
        raise ValidationError('Password must contain at least one uppercase letter')

    if not re.search(r'[a-z]', password1):
        raise ValidationError('Password must contain at least one lowercase letter')

    if not re.search(r'\d', password1):
        raise ValidationError('Password must contain at least one digit')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
        raise ValidationError('Password must contain at least one special character')

# SignUp View
def signup_view(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')
        first_name = request.POST.get('firstname')
        last_name = request.POST.get('lastname')
        password = re.match('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', pass1)

        if password is None:
            messages.error(request, 'Your password must be 8 characters and combination of one uppercase, one lowercase, one digit, and one special character atleast.')
            return redirect('signup')
        else:
            if pass1 != pass2:
                messages.error(request, 'Password and Confirm password are not matching')
                return redirect('signup')
            else:
                my_user = User.objects.create_user(uname, email, pass1)
                my_user.is_active = True
                my_user.first_name = first_name
                my_user.last_name = last_name
                my_user.save()
                messages.success(request, 'You have signed up successfully!')
                return redirect('signup')  
    return render(request, 'registration/signup.html')

# LogIn View
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Please fill out both fields.')
            return render(request, 'registration/login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            if user.is_staff:
                return redirect('/admin/')  # Redirect admins to admin interface
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

# Logout View
def logout_view(request):
    logout(request)
    messages.error(request, 'Logged out successfully!')
    return redirect('home')

# Finding Trips
def find_trips(request):
    trips = None
    if request.method == 'POST':
        departure = request.POST.get('departure')
        destination = request.POST.get('destination')
        date = request.POST.get('date')

        if departure and destination and date:
            trips = Schedule.objects.filter(
                depart__location__icontains=departure,
                destination__location__icontains=destination,
                schedule__date=date,
                status='1'
            )
            return render(request, 'reserve/all_trips.html', {'trips': trips})

    return render(request, 'reserve/find_trips.html')

# Book a Trip with Seat selection
@login_required
def book_trip(request, schedule_id):
    schedule = Schedule.objects.get(id=schedule_id)
    booked_seats = Booking.objects.filter(schedule=schedule).values_list('selected_seats', flat=True)
    booked_seats = [seat for sublist in booked_seats for seat in sublist]  # Flatten the list of lists
    seat_range = range(1, schedule.bus.seats + 1)

    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        selected_seats = [int(seat) for seat in selected_seats]  # Convert to integers

        if all(seat not in booked_seats for seat in selected_seats):
            booking = Booking(
                code='BKG' + str(timezone.now().timestamp()).replace('.', ''),
                name=request.user.first_name,
                schedule=schedule,
                seats=len(selected_seats),
                selected_seats=selected_seats,
                status='1'  # UnPaid status
            )
            booking.save()
            
            return redirect('booking-confirmation', booking_id=booking.id)
        else:
            error_message = "Some of the selected seats are not available."
            return render(request, 'reserve/book_trip.html', {'schedule': schedule, 'booked_seats': booked_seats, 'seat_range': seat_range, 'error_message': error_message})

    return render(request, 'reserve/book_trip.html', {'schedule': schedule, 'booked_seats': booked_seats, 'seat_range': seat_range})

# Booking Confirmation View & and Sending Mail to respective user
@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Prepare booking details
    from_location = booking.schedule.depart
    to_location = booking.schedule.destination
    booking_details = f"""
    Booking Code: {booking.code}
    Name: {booking.name}
    From: {from_location}
    To: {to_location}
    Schedule: {booking.schedule.schedule.strftime('%Y-%m-%d %H:%M')}
    Seats: {booking.seats}
    Total Payable: {booking.total_payable()}
    Status: {'Pending' if booking.status == '1' else 'Paid'}
    Date Created: {booking.date_created.strftime('%Y-%m-%d %H:%M')}
    """
    
    # Send email confirmation
    user_email = request.user.email
    send_booking_confirmation(user_email, booking_details)
    
    return render(request, 'reserve/booking_confirmation.html', {'booking': booking})
#--------------------------------------------------------------------------------------------

paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" in production
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@login_required
def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        try:
            # Format total payable amount to two decimal places
            total_amount = Decimal(booking.total_payable()).quantize(Decimal('0.01'))

            # Create PayPal Payment object
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(reverse('payment_success')),
                    "cancel_url": request.build_absolute_uri(reverse('payment_cancel'))
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"Booking {booking.code}",
                            "sku": f"booking_{booking.id}",
                            "price": "{:.2f}".format(total_amount),
                            "currency": "USD",
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": "{:.2f}".format(total_amount),
                        "currency": "USD"
                    },
                    "description": f"Payment for booking {booking.code}."
                }]
            })

            # Create the PayPal payment
            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = str(link.href)
                        return redirect(approval_url)
            else:
                logging.error(payment.error)
                return render(request, 'reserve/payment_page.html', {
                    'booking': booking,
                    'error': payment.error
                })
        except Exception as e:
            logging.error(str(e))
            return render(request, 'reserve/payment_page.html', {
                'booking': booking,
                'error': "An error occurred while processing your payment. Please try again later."
            })

    return render(request, 'reserve/payment_page.html', {
        'booking': booking
    })

@login_required
def payment_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    try:
        # Retrieve PayPal payment object by ID
        payment = paypalrestsdk.Payment.find(payment_id)
        
        # Execute the PayPal payment
        if payment.execute({"payer_id": payer_id}):
            booking_code = payment.transactions[0].item_list.items[0].sku.split('_')[1]
            booking = Booking.objects.get(id=booking_code)
            booking.status = '2'
            booking.save()

            from_location = booking.schedule.depart
            to_location = booking.schedule.destination
            booking_details = f"""
            Booking Code: {booking.code}
            Payment ID: {payment_id}
            Name: {booking.name}
            From: {from_location}
            To: {to_location}
            Schedule: {booking.schedule.schedule.strftime('%Y-%m-%d %H:%M')}
            Seats: {booking.seats}
            Total Payable: {booking.total_payable()}
            Status: {'Pending' if booking.status == '1' else 'Paid'}
            Date Created: {booking.date_created.strftime('%Y-%m-%d %H:%M')}
            """
            # Send email confirmation
            user_email = request.user.email
            send_booking_confirmation(user_email, booking_details)
            return render(request, 'reserve/payment_success.html')
        else:
            logging.error(payment.error)
            return render(request, 'reserve/payment_fail.html', {'error': payment.error})
    except Exception as e:
        logging.error(str(e))
        return render(request, 'reserve/payment_fail.html', {'error': "An error occurred while processing your payment. Please contact support."})

@login_required
def payment_cancel(request):
    return render(request, 'reserve/payment_cancel.html')


#---------------------------------------------------------------------------------------------
# Contact Us View
def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if name and email and subject and message:
            contact = Contact(name=name, email=email, subject=subject, message=message)
            contact.save()
            messages.success(request, 'Thank you for contacting us.\nWe will get back to you soon.')
            return redirect('contact-us')
        else:
            messages.error(request, 'Please fill in all fields.')

    return render(request, 'reserve/contact_us.html')

# Update User Profile
@login_required
@require_POST
def update_profile(request):
    user = request.user
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')

    # Update user details
    user.first_name = first_name
    user.last_name = last_name
    user.email = email

    if password and password == confirm_password:
        user.set_password(password)

    user.save()

    return JsonResponse({'status': 'success'})

# View All Schedules with Sorting and Pagination
def schedule_list(request):
    # Update status of schedules behind today's date and time
    now = timezone.now()
    Schedule.objects.filter(schedule__lt=now).update(status='2')

    # Sorting logic based on query parameter 'sort'
    sort_by = request.GET.get('sort')
    if sort_by:
        if sort_by.endswith('_asc'):
            field = sort_by[:-4]  # Remove '_asc' suffix
            schedules_list = Schedule.objects.order_by(field)
        elif sort_by.endswith('_desc'):
            field = sort_by[:-5]  # Remove '_desc' suffix
            schedules_list = Schedule.objects.order_by(f'-{field}')
        else:
            schedules_list = Schedule.objects.all()
    else:
        schedules_list = Schedule.objects.all()

    # Pagination
    paginator = Paginator(schedules_list, 10)
    page_number = request.GET.get('page')
    schedules = paginator.get_page(page_number)
    
    context = {
        'schedules': schedules,
        'sort_by': sort_by
    }
    return render(request, 'reserve/schedule_list.html', context)

# View All User Booking with Pagination
@login_required
def user_bookings(request):
    bookings_list = Booking.objects.filter(name=request.user.first_name)
    paginator = Paginator(bookings_list, 5)

    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)
    return render(request, 'reserve/user_bookings.html', {'bookings': bookings})

# View all Categories
@login_required
def all_categories(request):
    categories_list = Category.objects.all()
    paginator = Paginator(categories_list, 5)  

    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    return render(request, 'reserve/all_categories.html',{'categories':categories})

# View all Buses with sorting and pagination
@login_required
def all_buses(request):
    query = request.GET.get('q')
    if query:
        buses_list = Bus.objects.filter(
            Q(bus_number__icontains=query) | Q(category__name__icontains=query)
        )
    else:
        buses_list = Bus.objects.all()

    paginator = Paginator(buses_list, 5)

    page_number = request.GET.get('page')
    buses = paginator.get_page(page_number)
    return render(request, 'reserve/bus_list.html', {'buses': buses, 'query': query})

# View all Locations with sorting
@login_required
def all_locations(request):
    query = request.GET.get('q')
    sort = request.GET.get('sort', 'name_asc')
    
    if query:
        locations_list = Location.objects.filter(location__icontains=query)
    else:
        locations_list = Location.objects.all()
    
    if sort == 'name_asc':
        locations_list = locations_list.order_by('location')
    elif sort == 'name_desc':
        locations_list = locations_list.order_by('-location')
    elif sort == 'id_asc':
        locations_list = locations_list.order_by('id')
    elif sort == 'id_desc':
        locations_list = locations_list.order_by('-id')
    
    paginator = Paginator(locations_list, 10)
    page_number = request.GET.get('page')
    locations = paginator.get_page(page_number)
    
    return render(request, 'reserve/location_list.html', {'locations': locations, 'query': query})

# View for canceling a booking
@login_required
def cancel_booking(request):
    booking_id = request.GET.get('id')
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status == '1':  
        booking.status = '3'  
        booking.save()

        from_location = booking.schedule.depart
        to_location = booking.schedule.destination
        booking_details = f"""
            Booking Code: {booking.code}
            Name: {booking.name}
            From: {from_location}
            To: {to_location}
            Schedule: {booking.schedule.schedule.strftime('%Y-%m-%d %H:%M')}
            Seats: {booking.seats}
            Total Payable: {booking.total_payable()}
            Status: Canceled
            Date Created: {booking.date_created.strftime('%Y-%m-%d %H:%M')}
            """
        # Send email
        user_email = request.user.email
        send_booking_confirmation(user_email, booking_details)
        messages.success(request, 'Booking has been successfully cancelled.')
    else:
        messages.error(request, 'Only pending bookings can be cancelled.')

    return redirect('user-bookings')  

# View for delete a booking
@login_required
def delete_booking(request):
    booking_id = request.GET.get('id')
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != '1':  
        booking.delete()
        messages.success(request, 'Booking has been successfully deleted.')
    else:
        messages.error(request, 'Pending bookings cannot be deleted. Please cancel them instead.')

    return redirect('user-bookings')  
