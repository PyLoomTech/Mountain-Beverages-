from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import redirect, render

from orders.models import Order

from .forms import ReviewForm
from .models import Review


def review_list(request):
    reviews = Review.objects.filter(status="approved").select_related("customer")
    average = reviews.aggregate(avg=Avg("rating"))["avg"]
    return render(request, "reviews/review_list.html", {
        "reviews": reviews,
        "average": average,
        "count": reviews.count(),
    })


@login_required
def review_create(request):
    existing = Review.objects.filter(customer=request.user).first()
    eligible = Order.objects.filter(customer=request.user, status="delivered").exists()

    form = None
    if not existing and eligible:
        if request.method == "POST":
            form = ReviewForm(request.POST)
            if form.is_valid():
                review = form.save(commit=False)
                review.customer = request.user
                review.save()  # status defaults to "pending"
                messages.success(
                    request,
                    "Thank you! Your review has been submitted and will appear after approval.",
                )
                return redirect("review_create")
        else:
            form = ReviewForm()

    return render(request, "reviews/review_form.html", {
        "form": form,
        "existing": existing,
        "eligible": eligible,
    })