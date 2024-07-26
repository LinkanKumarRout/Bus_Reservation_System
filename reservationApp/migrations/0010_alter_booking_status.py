# Generated by Django 5.0.6 on 2024-07-09 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservationApp', '0009_location_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(choices=[('1', 'Pending'), ('2', 'Paid'), ('3', 'Cancelled')], default='1', max_length=2),
        ),
    ]