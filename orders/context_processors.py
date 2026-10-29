from .cart import CART_SESSION_KEY


def cart_count(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    return {"cart_count": sum(cart.values())}