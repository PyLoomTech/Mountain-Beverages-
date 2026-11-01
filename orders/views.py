from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product

from .cart import MAX_QUANTITY, Cart
from .forms import CheckoutForm
from .models import Order, OrderItem


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


# ---------- Cart ----------

def cart_detail(request):
    items, total = Cart(request).items_and_total()
    return render(request, "orders/cart.html", {"items": items, "total": total})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1
    quantity = max(1, min(quantity, MAX_QUANTITY))

    cart = Cart(request)
    cart.add(product, quantity)

    # "Order Now" goes straight to checkout
    if request.POST.get("action") == "buy":
        return redirect("checkout")

    message = f"{product.name} added to your cart."

    # "Add to Cart" from the product page: answer the background request, no page change
    if is_ajax(request):
        return JsonResponse({"ok": True, "message": message, "cart_count": cart.count()})

    messages.success(request, message)
    return redirect("cart_detail")


@require_POST
def cart_update(request, product_id):
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        return redirect("cart_detail")
    Cart(request).set_quantity(product_id, quantity)
    messages.success(request, "Your cart has been updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    messages.info(request, "Item removed from your cart.")
    return redirect("cart_detail")


# ---------- Checkout ----------

@login_required
def checkout(request):
    cart = Cart(request)
    items, total = cart.items_and_total()

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("product_list")

    unavailable = [i["product"].name for i in items if not i["product"].is_available]
    if unavailable:
        messages.error(
            request,
            "These products are no longer available: " + ", ".join(unavailable) + ". Please remove them.",
        )
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.customer = request.user
                order.save()
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["product"].price,  # price frozen at order time
                    )
                    for item in items
                ])
            cart.clear()
            messages.success(request, f"Order #{order.pk} placed successfully!")
            return redirect("order_success", pk=order.pk)
    else:
        form = CheckoutForm(initial={
            "full_name": request.user.get_full_name(),
            "phone": request.user.phone,
            "address": request.user.address,
        })

    return render(request, "orders/checkout.html", {"form": form, "items": items, "total": total})


# ---------- Customer orders ----------

@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    return render(request, "orders/order_success.html", {"order": order})


@login_required
def order_list(request):
    orders = Order.objects.filter(customer=request.user).prefetch_related("items")
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    # Filtering by customer means nobody can open another person's order
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"), pk=pk, customer=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})