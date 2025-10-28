from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.contrib import messages  # <- add

class ProfileCompletionMiddleware(MiddlewareMixin):
    """
    Redirect authenticated users with incomplete profiles to the profile page.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        path = request.path or "/"

        # Allow static, media and dev reload endpoint
        if (settings.STATIC_URL and path.startswith(settings.STATIC_URL)) \
           or (getattr(settings, "MEDIA_URL", None) and path.startswith(settings.MEDIA_URL)) \
           or path.startswith("/__reload__/"):
            return None

        match = getattr(request, "resolver_match", None)
        view_name = getattr(match, "view_name", None)
        url_name = getattr(match, "url_name", None)
        app_name = getattr(match, "app_name", None)

        allowed_view_names = {
            "profile", "users:profile",
            "profile_create", "users:profile_create",
            "login", "logout", "register",
            "password_change", "password_reset",
            "password_reset_done", "password_reset_confirm", "password_reset_complete",
            "account_login", "account_logout", "account_signup",
        }

        # Resolve profile URLs to also allow by path
        try:
            profile_url = reverse("profile")
        except Exception:
            profile_url = "/profile/"
        try:
            profile_create_url = reverse("profile_create")
        except Exception:
            profile_create_url = "/profile/create/"

        if (url_name in allowed_view_names) or (view_name in allowed_view_names) \
           or (app_name in {"admin", "account", "socialaccount"}) \
           or path.startswith("/admin/") \
           or path in {profile_url, profile_create_url}:
            return None

        # Safe completeness check
        user = request.user
        first = (getattr(user, "first_name", "") or "").strip()
        last  = (getattr(user, "last_name", "") or "").strip()
        try:
            profile = user.profile
        except Exception:
            profile = None

        complete = False
        if profile is not None:
            ic = getattr(profile, "is_complete", None)
            if ic is not None:
                complete = ic() if callable(ic) else bool(ic)
            else:
                first = (getattr(profile, "first_name", "") or first).strip()
                last  = (getattr(profile, "last_name", "") or last).strip()
                complete = bool(first and last)
        else:
            complete = bool(first and last)

        if not complete:
            # Allow staying on the profile/profile_create pages
            if view_name in {"profile", "users:profile", "profile_create", "users:profile_create"}:
                return None

            target = profile_create_url if profile is None else profile_url
            if path == target:
                return None

            # Notify user
            messages.info(request, "Please complete your profile to continue. Redirecting to setup...")

            next_url = request.get_full_path()
            if next_url == target:
                return redirect(target)
            return redirect(f"{target}?next={next_url}")

        return None