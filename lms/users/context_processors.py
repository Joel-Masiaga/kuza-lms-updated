from .models import SubscribedUser

def subscription_context(request):
    is_subscribed = False
    if request.user.is_authenticated:
        subscription = SubscribedUser.objects.filter(user=request.user).first()
        if subscription and subscription.subscribed:
            is_subscribed = True
    return {
        'is_subscribed': is_subscribed,
    }