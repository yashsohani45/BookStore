from .models import CartItem
from .models import Language

def language_list(request):
    languages = Language.objects.all()
    return {'language_list': languages}


def cart_items_count(request):
    count = 0
    if request.user.is_authenticated:
        count = CartItem.objects.filter(user=request.user).count()
    return {'cart_items_count': count}