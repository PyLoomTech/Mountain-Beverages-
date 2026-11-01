from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


def _is_site_request(request):
    """True for normal site requests (skips the admin and non-web logins)."""
    return request is not None and not request.path.startswith("/admin/")


@receiver(user_logged_in)
def welcome_back(sender, request, user, **kwargs):
    if not _is_site_request(request):
        return
    
    if getattr(request, "skip_login_toast", False):
        return
    name = user.first_name or user.username
    messages.success(request, f"Welcome back, {name}!", fail_silently=True)

@receiver(user_logged_out)
def goodbye(sender, request, user, **kwargs):
    if not _is_site_request(request):
        return
    messages.info(request, "You have been logged out.", fail_silently=True)