# Generated by Django 4.2.13 on 2024-06-24 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservationApp', '0002_alter_schedule_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='code',
            field=models.CharField(max_length=100),
        ),
    ]
