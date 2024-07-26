# Generated by Django 4.2.13 on 2024-06-24 12:38

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('reservationApp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='code',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]