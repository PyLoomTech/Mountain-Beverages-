from catalog.models import Product

CART_SESSION_KEY = "cart"
MAX_QUANTITY = 999


class Cart:
    """Shopping cart stored in the user's session as {product_id: quantity}."""

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(CART_SESSION_KEY, {})

    def _save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True

    def add(self, product, quantity=1):
        key = str(product.pk)
        self.cart[key] = min(self.cart.get(key, 0) + quantity, MAX_QUANTITY)
        self._save()

    def set_quantity(self, product_id, quantity):
        key = str(product_id)
        if key not in self.cart:
            return
        if quantity <= 0:
            del self.cart[key]
        else:
            self.cart[key] = min(quantity, MAX_QUANTITY)
        self._save()

    def remove(self, product_id):
        self.cart.pop(str(product_id), None)
        self._save()

    def clear(self):
        self.cart = {}
        self._save()

    def count(self):
        """Total number of units in the cart (shown in the navbar badge)."""
        return sum(self.cart.values())

    def items_and_total(self):
        """Return (list of items, total price). One database query."""
        products = Product.objects.filter(pk__in=self.cart.keys()).select_related("category")
        items = []
        total = 0
        for product in products:
            quantity = self.cart[str(product.pk)]
            subtotal = product.price * quantity
            total += subtotal
            items.append({"product": product, "quantity": quantity, "subtotal": subtotal})
        return items, total