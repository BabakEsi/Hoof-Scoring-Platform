from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=False)
    token_send = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ]

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('scorer', 'Scorer'),
        ('tester', 'Tester'),
    ]

    status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default="pending"
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        blank=True,
        default=""
    )


    otp_created_at = models.DateTimeField(
        blank=True,
        null=True
    )

    def is_admin(self):
        return self.role == 'admin'

