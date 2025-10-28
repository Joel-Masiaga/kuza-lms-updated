from django.shortcuts import render, redirect
from django.conf import settings
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib.auth import logout
from django.contrib.auth import login, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.models import User
from .models import SubscribedUser
from .forms import NewsLetterForm 
from django.contrib import messages

from django.core.mail import EmailMessage
from django.core.validators import  validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import get_object_or_404

# Register View
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'student'
            user.save()

            # Explicit backend to avoid ValueError (multiple auth backends)
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

            messages.success(request, "Registration successful! Please complete your profile.")
            next_url = request.GET.get('next')
            return redirect(next_url or 'profile_create')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

# Login View
def custom_login(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # email used as username
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
                messages.success(request, "Login successful. Welcome back!")
                return redirect('home')
            else:
                messages.error(request, "Invalid credentials. Please try again.")
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def custom_logout(request):
    logout(request)  # Log out the user
    return redirect('logout')  # Redirect to the logged_out page

# Profile Update View
@login_required
def profile(request):
    # Check if the user has a profile
    if not hasattr(request.user, 'profile') or request.user.profile is None:
        # If not, redirect them to the profile creation page
        return redirect('profile_create')  # Make sure to create a 'profile_create' view
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profile')  # Redirect to the profile page after successful update
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile.html', context)

@login_required
def profile_create(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES)

        if u_form.is_valid() and p_form.is_valid():
            user = u_form.save()
            profile = p_form.save(commit=False)
            profile.user = user  # Assign the profile to the user
            profile.save()
            return redirect('profile')  # Redirect to the profile page after profile creation
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm()

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile_create.html', context)

# Subscription viewsfrom django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import SubscribedUser, User

@login_required
def subscribe(request):
    if request.method == 'POST':
        user = request.user
        
        # Ensure the user has an email
        if not user.email:
            messages.error(request, "Please update your profile with a valid email before subscribing.")
            return redirect('profile')

        # Validate email format
        try:
            validate_email(user.email)
        except ValidationError:
            messages.error(request, "Your email is invalid. Please update your profile with a valid email before subscribing.")
            return redirect('profile')

        # Check if the email is correctly associated with the logged-in user
        if not User.objects.filter(id=user.id, email=user.email).exists():
            messages.error(request, "Your email does not match our records. Please update your profile with the correct email.")
            return redirect('profile')

        # Avoid duplicate subscriptions
        subscription, created = SubscribedUser.objects.get_or_create(user=user, defaults={'subscribed': True})
        
        if created:
            messages.success(request, "You have successfully subscribed!")
        else:
            messages.info(request, "You are already subscribed.")

    return redirect('home')


@login_required
def unsubscribe(request):
    if request.method == 'POST':
        user = request.user
         
        # Ensure the user has an email
        if not user.email:
            messages.error(request, "Please update your profile with a valid email before unsubscribing.")
            return redirect('profile')

        # Validate email format
        try:
            validate_email(user.email)
        except ValidationError:
            messages.error(request, "Your email is invalid. Please update your profile with a valid email before unsubscribing.")
            return redirect('profile')

        # Check if the email is correctly associated with the logged-in user
        if not User.objects.filter(id=user.id, email=user.email).exists():
            messages.error(request, "Your email does not match our records. Please update your profile with the correct email before unsubscribing.")
            return redirect('profile')

        # Check if the user has a subscription
        subscription = SubscribedUser.objects.filter(user=user)
        if subscription.exists():
            subscription.delete()
            messages.success(request, "You have successfully unsubscribed.")
        else:
            messages.info(request, "You were not subscribed.")

    return redirect('home')


def superuser_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('home') 
        return view_func(request, *args, **kwargs)
    return wrapper

@superuser_required
def newsletter(request):
    if request.method == 'POST':
        form = NewsLetterForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data.get('subject')
            receivers = form.cleaned_data.get('receivers').split(',')
            message = form.cleaned_data.get('message')
           
           
            mail = EmailMessage(subject, message, f'Soma Online <{request.user.email}>', bcc=receivers)
            mail.content_subtype = 'html'

            if mail.send():
                messages.success(request, "Newsletter sent successfully.")
            else:
                messages.error(request, "Failed to send newsletter.")

        else: 
            for error in list(form.errors.values()):
                messages.error(request, error)
           
        return redirect('home')

    form = NewsLetterForm()
    form.fields['receivers'].initial = ','.join([active.user.email for active in SubscribedUser.objects.all()])
    return render(request=request, template_name='users/newsletter.html', context={'form': form})
        

