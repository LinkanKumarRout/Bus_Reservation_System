from django.core.mail import send_mail
from django.conf import settings

def send_booking_confirmation(user_email, booking_details):
    subject = 'Busify | Booking Confirmation'
    message = f'Thank you for your booking.\n\nHere are the booking details:\n{booking_details}\n\nThank You.\nWish you a Happy Journey\nTeam Busify'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [user_email]
    send_mail(subject, message, email_from, recipient_list)
