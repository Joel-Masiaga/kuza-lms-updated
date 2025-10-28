from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Profile, SubscribedUser

# Inline: Profile on User page
class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 0
    can_delete = False
    fields = (
        ('first_name', 'last_name'),
        ('address', 'country'),
        'image',
        'points',
        'earned_badges',
        'image_preview',
    )
    readonly_fields = ('image_preview',)

    def image_preview(self, instance):
        if instance and instance.image:
            try:
                return format_html('<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:6px;" />', instance.image.url)
            except Exception:
                return "-"
        return "-"
    image_preview.short_description = "Avatar"

# Inline: Subscription on User page
class SubscribedUserInline(admin.StackedInline):
    model = SubscribedUser
    extra = 0
    can_delete = False
    fields = ('subscribed', 'created_at')
    readonly_fields = ('created_at',)

# Custom User admin
class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'role', 'points', 'subscribed', 'is_staff', 'is_active', 'is_superuser']
    list_filter = ['role', 'is_staff', 'is_superuser', 'subscription__subscribed']
    search_fields = ['email', 'profile__first_name', 'profile__last_name']
    inlines = [ProfileInline, SubscribedUserInline]

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('role',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

    def points(self, obj):
        return getattr(getattr(obj, 'profile', None), 'points', 0)
    points.short_description = 'Points'

    def subscribed(self, obj):
        return getattr(getattr(obj, 'subscription', None), 'subscribed', False)
    subscribed.boolean = True
    subscribed.short_description = 'Subscribed'

# Profile admin (direct list view)
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'points', 'badges_count', 'country', 'avatar')
    search_fields = ('user__email', 'first_name', 'last_name', 'country')
    list_filter = ('country',)
    readonly_fields = ('avatar',)
    fields = (
        'user',
        ('first_name', 'last_name'),
        ('address', 'country'),
        'image',
        'avatar',
        'points',
        'earned_badges',
    )

    def badges_count(self, obj):
        return obj.earned_badges.count()
    badges_count.short_description = 'Badges'

    def avatar(self, obj):
        if obj.image:
            try:
                return format_html('<img src="{}" style="height:64px;width:64px;object-fit:cover;border-radius:8px;" />', obj.image.url)
            except Exception:
                return "-"
        return "-"
    avatar.short_description = 'Avatar'

class SubscribedUserAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'subscribed', 'created_at']
    list_filter = ['subscribed', 'created_at']
    search_fields = ['user__email']

    def user_email(self, obj):
        return obj.user.email

# Register the custom User model and others
admin.site.register(User, UserAdmin)
admin.site.register(SubscribedUser, SubscribedUserAdmin)

# Optional: Branding
admin.site.site_header = "Kuza Ndoto Admin"
admin.site.site_title = "Kuza Ndoto Admin"
admin.site.index_title = "Dashboard"