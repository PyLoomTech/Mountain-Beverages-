from django.contrib import messages
from django.shortcuts import redirect, render

from catalog.models import Product
from projects.models import Project
from reviews.models import Review

from .forms import ContactForm
from .models import Announcement, Highlight, TeamMember


def home(request):
    available = Product.objects.filter(is_available=True).select_related("category")
    featured_products = available.filter(is_featured=True)[:4] or available[:4]

    projects = Project.objects.filter(is_published=True)
    featured_projects = projects.filter(is_featured=True)[:3] or projects[:3]

    reviews = Review.objects.filter(status="approved").select_related("customer")[:3]

    return render(request, "core/home.html", {
        "featured_products": featured_products,
        "featured_projects": featured_projects,
        "reviews": reviews,
        "highlights": Highlight.objects.filter(is_active=True),
        "announcement": Announcement.current(),
    })


def about(request):
    return render(request, "core/about.html", {
        "team": TeamMember.objects.filter(is_active=True),
    })


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your message has been sent. We will contact you soon.")
            return redirect("contact")
    else:
        form = ContactForm()
    return render(request, "core/contact.html", {"form": form})