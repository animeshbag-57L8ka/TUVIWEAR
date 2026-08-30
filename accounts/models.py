from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Others', 'Others'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    real_name = models.CharField(
        max_length=150
    )

    mobile = models.CharField(
        max_length=15
    )

    age = models.PositiveIntegerField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='Others'
    )

    location = models.CharField(
        max_length=200
    )

    # =========================================================
    # DELIVERY INFORMATION
    # =========================================================

    address = models.TextField(
        blank=True,
        default=''
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
        default=''
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.real_name}"