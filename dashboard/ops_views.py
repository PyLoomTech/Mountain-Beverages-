"""
Day-to-day work: orders, reviews, contact messages and customers.

Unlike the content sections in registry.py, these screens have their own actions
(change an order's status, approve a review, mark a message as read, ...).
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.models import ContactMessage
from orders.models import Order
from reviews.models import Review

from .permissions import staff_required
from .views import PAGE_SIZE, page, safe_next

User = get_user_model()


def paginate(request, queryset):
    """Return (page, query string without 'page') so pager links keep the filters."""
    page_obj = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page_obj, params.urlencode()


def status_tabs(model, choices, current):
    """Tabs such as All / Pending / Confirmed, each with a count."""
    counts = dict(model.objects.order_by().values_list("status").annotate(n=Count("pk")))
    tabs = [{"label": "All", "value": "", "count": sum(counts.values()), "active": current == ""}]
    for value, label in choices:
        tabs.append({
            "label": label, "value": value,
            "count": counts.get(value, 0), "active": current == value,
        })
    return tabs


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@staff_required
def orders_list(request):
    valid = {value for value, _ in Order.STATUS_CHOICES}
    status = request.GET.get("status", "")
    status = status if status in valid else ""
    q = request.GET.get("q", "").strip()

    queryset = Order.objects.select_related("customer").prefetch_related("items")
    if status:
        queryset = queryset.filter(status=status)
    if q:
        condition = (
            Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(customer__username__icontains=q)
        )
        number = q.lstrip("#")
        if number.isdigit():
            condition |= Q(pk=int(number))
        queryset = queryset.filter(condition)

    page_obj, query_string = paginate(request, queryset)
    return page(request, "dashboard/orders_list.html", {
        "page_obj": page_obj,
        "query_string": query_string,
        "q": q,
        "status": status,
        "tabs": status_tabs(Order, Order.STATUS_CHOICES, status),
        "current_url": request.get_full_path(),
    }, active="orders")


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("items__product"), pk=pk
    )
    return page(request, "dashboard/order_detail.html", {
        "order": order,
        "statuses": Order.STATUS_CHOICES,
    }, active="orders")


@staff_required
@require_POST
def order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get("status", "")

    if new_status not in dict(Order.STATUS_CHOICES):
        messages.error(request, "Please choose a valid status.")
    elif new_status == order.status:
        messages.info(request, f"Order #{order.pk} is already {order.get_status_display().lower()}.")
    else:
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Order #{order.pk} is now {order.get_status_display().lower()}.")

    return redirect(safe_next(request, reverse("dashboard:order_detail", args=[order.pk])))


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@staff_required
def reviews_list(request):
    valid = {value for value, _ in Review.STATUS_CHOICES}
    status = request.GET.get("status", "")
    status = status if status in valid else ""
    q = request.GET.get("q", "").strip()

    queryset = Review.objects.select_related("customer")
    if status:
        queryset = queryset.filter(status=status)
    if q:
        queryset = queryset.filter(
            Q(comment__icontains=q) | Q(customer__username__icontains=q)
            | Q(customer__first_name__icontains=q) | Q(customer__last_name__icontains=q)
        )

    page_obj, query_string = paginate(request, queryset)
    return page(request, "dashboard/reviews_list.html", {
        "page_obj": page_obj,
        "query_string": query_string,
        "q": q,
        "status": status,
        "tabs": status_tabs(Review, Review.STATUS_CHOICES, status),
        "current_url": request.get_full_path(),
    }, active="reviews")


@staff_required
@require_POST
def review_status(request, pk):
    review = get_object_or_404(Review, pk=pk)
    new_status = request.POST.get("status", "")

    if new_status not in dict(Review.STATUS_CHOICES):
        messages.error(request, "Please choose a valid status.")
    else:
        review.status = new_status
        review.save(update_fields=["status"])
        messages.success(request, f"Review by {review.customer} is now {review.get_status_display().lower()}.")

    return redirect(safe_next(request, reverse("dashboard:reviews")))


@staff_required
def review_delete(request, pk):
    review = get_object_or_404(Review.objects.select_related("customer"), pk=pk)

    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect("dashboard:reviews")

    return page(request, "dashboard/confirm_delete.html", {
        "title": "Delete review?",
        "obj": f"the review by {review.customer}",
        "cancel_url": reverse("dashboard:reviews"),
        "hint": "If you only want to hide it from the website, use Reject instead.",
    }, active="reviews")


# ---------------------------------------------------------------------------
# Contact messages
# ---------------------------------------------------------------------------

@staff_required
def inbox(request):
    show = request.GET.get("filter", "")
    show = show if show == "unread" else ""
    q = request.GET.get("q", "").strip()

    queryset = ContactMessage.objects.all()
    if show == "unread":
        queryset = queryset.filter(is_read=False)
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(message__icontains=q)
        )

    page_obj, query_string = paginate(request, queryset)
    return page(request, "dashboard/inbox.html", {
        "page_obj": page_obj,
        "query_string": query_string,
        "q": q,
        "show": show,
        "total": ContactMessage.objects.count(),
        "unread": ContactMessage.objects.filter(is_read=False).count(),
    }, active="inbox")


@staff_required
def message_detail(request, pk):
    contact = get_object_or_404(ContactMessage, pk=pk)
    if not contact.is_read:  # opening a message marks it as read
        contact.is_read = True
        contact.save(update_fields=["is_read"])
    return page(request, "dashboard/message_detail.html", {"contact": contact}, active="inbox")


@staff_required
@require_POST
def message_unread(request, pk):
    contact = get_object_or_404(ContactMessage, pk=pk)
    contact.is_read = False
    contact.save(update_fields=["is_read"])
    messages.success(request, "Marked as unread.")
    return redirect("dashboard:inbox")


@staff_required
def message_delete(request, pk):
    contact = get_object_or_404(ContactMessage, pk=pk)

    if request.method == "POST":
        contact.delete()
        messages.success(request, "Message deleted.")
        return redirect("dashboard:inbox")

    return page(request, "dashboard/confirm_delete.html", {
        "title": "Delete message?",
        "obj": f"the message from {contact.name}",
        "cancel_url": reverse("dashboard:message_detail", args=[contact.pk]),
        "hint": "",
    }, active="inbox")


# ---------------------------------------------------------------------------
# Customers (staff accounts are managed in the Django admin)
# ---------------------------------------------------------------------------

@staff_required
def customers_list(request):
    q = request.GET.get("q", "").strip()

    queryset = (
        User.objects.filter(is_staff=False)
        .annotate(order_count=Count("orders", distinct=True))
        .order_by("-date_joined")
    )
    if q:
        queryset = queryset.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    page_obj, query_string = paginate(request, queryset)
    return page(request, "dashboard/customers_list.html", {
        "page_obj": page_obj,
        "query_string": query_string,
        "q": q,
    }, active="customers")


@staff_required
def customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    return page(request, "dashboard/customer_detail.html", {
        "customer": customer,
        "orders": customer.orders.prefetch_related("items"),
        "reviews": customer.reviews.all(),
    }, active="customers")


@staff_required
@require_POST
def customer_active(request, pk):
    """Block or allow a customer to log in. Their orders and reviews are kept."""
    customer = get_object_or_404(User, pk=pk, is_staff=False)
    customer.is_active = not customer.is_active
    customer.save(update_fields=["is_active"])
    state = "can log in again" if customer.is_active else "can no longer log in"
    messages.success(request, f"{customer} {state}.")
    return redirect("dashboard:customer_detail", pk=pk)
