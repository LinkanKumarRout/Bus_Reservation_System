# Generated by Django 4.2.13 on 2024-06-26 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservationApp', '0004_alter_schedule_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='bus',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='bus_images/'),
        ),
    ]