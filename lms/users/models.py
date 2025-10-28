from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from PIL import Image
from django.db.models import Sum # Import Sum for calculating points
import os

# Custom manager for User model
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

# Custom User model with email-based authentication
class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=255)
    username = None  # We are not using the username field
    role_choices = [
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    ]
    role = models.CharField(max_length=10, choices=role_choices, default='student')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Only email and password are required

    def __str__(self):
        return self.email

    def is_student(self):
        return self.role == 'student'

    def is_instructor(self):
        return self.role == 'instructor'

# Profile model for storing additional user information
class Profile(models.Model):
    image = models.ImageField(default='default.jpg', upload_to='profile_pics/', blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True) 
    address = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='profile')

    points = models.PositiveIntegerField(default=0)
    earned_badges = models.ManyToManyField('courses.Course', blank=True, related_name='awarded_to')
    
    
    def __str__(self):
        return f"Profile of {self.first_name} {self.last_name} ({self.user.email})"

    def save(self, *args, **kwargs):
        super().save()

        img = Image.open(self.image.path)

        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
            
    @property
    def is_complete(self):
        return bool((self.first_name or "").strip() and (self.last_name or "").strip()) 

# Subscription model for storing user subscriptions
class SubscribedUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    created_at = models.DateTimeField(auto_now_add=True)
    subscribed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - Subscribed: {self.subscribed}"