from django.db import models
from django.utils import timezone
from django.db.models import Sum
import random
import string

def generate_unique_code():
    timestamp_str = str(int(timezone.now().timestamp()))  # Get current timestamp as string
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generate random 6-character string
    return timestamp_str + '-' + random_chars  


class Category(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField()
    status = models.CharField(max_length=2, choices=(('1','Active'),('2','Inactive')), default=1)
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    location = models.CharField(max_length=250)
    status = models.CharField(max_length=2, choices=(('1','Active'),('2','Inactive')), default=1)
    image = models.ImageField(upload_to='location_images/', blank=True, null=True)
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.location

class Bus(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE, blank= True, null = True)
    bus_number = models.CharField(max_length=250)
    seats = models.IntegerField()
    status = models.CharField(max_length=2, choices=(('1','Active'),('2','Inactive')), default=1)
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='bus_images/', blank=True, null=True)

    def __str__(self):
        return self.bus_number

class Schedule(models.Model):
    code = models.CharField(max_length=20, default=generate_unique_code, unique=True)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    depart = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='depart_location')
    destination = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='destination')
    schedule = models.DateTimeField()
    fare = models.FloatField()
    status = models.CharField(max_length=2, choices=(('1', 'Active'), ('2', 'Cancelled')), default='1')
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.code + ' - ' + self.bus.bus_number)

    def count_available(self):
        booked = Booking.objects.filter(schedule=self).aggregate(Sum('seats'))['seats__sum'] or 0
        return self.bus.seats - booked

    def get_available_seats(self):
        booked_seats = Booking.objects.filter(schedule=self).values_list('selected_seats', flat=True)
        booked_seats = [seat for sublist in booked_seats for seat in sublist]  # Flatten the list of lists
        return [seat for seat in range(1, self.bus.seats + 1) if seat not in booked_seats]

class Booking(models.Model):
    STATUS_CHOICES = (
        ('1', 'Pending'),
        ('2', 'Paid'),
        ('3', 'Cancelled'),  # Added Cancelled status
    )

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE)
    seats = models.PositiveIntegerField(default=0)
    selected_seats = models.JSONField(default=list)  # Store selected seats
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='1')
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def total_payable(self):
        return self.seats * self.schedule.fare

class Contact(models.Model):
    name = models.CharField(max_length=250)
    email = models.EmailField()
    subject = models.CharField(max_length=250)
    message = models.TextField()
    date_submitted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.subject

