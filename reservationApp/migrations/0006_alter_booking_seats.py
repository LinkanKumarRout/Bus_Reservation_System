# Generated by Django 4.2.13 on 2024-06-26 13:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservationApp', '0005_bus_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booking',
            name='seats',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
