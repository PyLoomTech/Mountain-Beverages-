from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import Announcement, ContactMessage, SiteSettings
from orders.models import Order
from projects.models import Project, ProjectImage
from reviews.models import Review

from .forms import MAX_IMAGE_MB, build_form_class, validate_image_size
from .permissions import staff_required
from .registry import NAV_GROUPS, SECTIONS, SITE_FIELDS, SITE_GROUPS

PAGE_SIZE = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def page(request, template, context=None, active=""):
    """Render a dashboard page with the sidebar information added."""
    context = dict(context or {})
    context.update({"nav_groups": NAV_GROUPS, "active": active})
    return render(request, template, context)


def get_section(key):
    section = SECTIONS.get(key)
    if section is None:
        raise Http404("Unknown dashboard section")
    return section


def resolve(obj, path):
    """Read a field, property or 'relation.method' from an object."""
    *parents, last = path.split(".")
    for part in parents:
        obj = getattr(obj, part)
    value = getattr(obj, last)
    return value() if callable(value) else value


def safe_next(request, fallback):
    """Return the 'next' address from the form if it points to this site."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return target
    return fallback


# ---------------------------------------------------------------------------
# Dashboard home
# ---------------------------------------------------------------------------

@staff_required
def home(request):
    content_cards = [
        {
            "label": section.label,
            "count": section.model._default_manager.count(),
            "icon": section.icon,
            "url": reverse("dashboard:list", args=[section.key]),
        }
        for section in SECTIONS.values()
    ]

    # Orders, reviews and messages move into the dashboard in a later step.
    # Until then these cards open the matching Django admin screen.
    work_cards = [
        {
            "label": "Pending orders",
            "count": Order.objects.filter(status="pending").count(),
            "icon": "bi-receipt",
            "url": reverse("admin:orders_order_changelist") + "?status__exact=pending",
        },
        {
            "label": "Reviews to approve",
            "count": Review.objects.filter(status="pending").count(),
            "icon": "bi-star-half",
            "url": reverse("admin:reviews_review_changelist") + "?status__exact=pending",
        },
        {
            "label": "Unread messages",
            "count": ContactMessage.objects.filter(is_read=False).count(),
            "icon": "bi-envelope",
            "url": reverse("admin:core_contactmessage_changelist") + "?is_read__exact=0",
        },
    ]

    return page(request, "dashboard/home.html", {
        "content_cards": content_cards,
        "work_cards": work_cards,
        "live_announcement": Announcement.current(),
    }, active="home")


# ---------------------------------------------------------------------------
# Site content (company text, banner, contact, social links)
# ---------------------------------------------------------------------------

@staff_required
def site_content(request):
    site = SiteSettings.load()
    Form = build_form_class(SiteSettings, SITE_FIELDS)

    if request.method == "POST":
        form = Form(request.POST, request.FILES, instance=site)
        if form.is_valid():
            form.save()
            messages.success(request, "Site content saved.")
            return redirect("dashboard:site")
    else:
        form = Form(instance=site)

    tabs = []
    for index, (title, icon, names) in enumerate(SITE_GROUPS):
        tabs.append({
            "id": f"tab{index}",
            "title": title,
            "icon": icon,
            "fields": [form[name] for name in names],
            "has_errors": any(form[name].errors for name in names),
        })

    # Open the first tab that has an error, otherwise the first tab
    active_tab = next((tab["id"] for tab in tabs if tab["has_errors"]), tabs[0]["id"])

    return page(request, "dashboard/site_form.html", {
        "form": form, "tabs": tabs, "active_tab": active_tab,
    }, active="site")


# ---------------------------------------------------------------------------
# Generic list / add / edit / delete / show-hide for every section
# ---------------------------------------------------------------------------

@staff_required
def section_list(request, key):
    section = get_section(key)
    queryset = section.model._default_manager.all()

    query = request.GET.get("q", "").strip()
    if query and section.search_fields:
        condition = Q()
        for field in section.search_fields:
            condition |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(condition)

    page_obj = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))

    rows = [
        {
            "obj": obj,
            "cells": [{"kind": col.kind, "value": resolve(obj, col.attr)} for col in section.columns],
        }
        for obj in page_obj
    ]

    return page(request, "dashboard/list.html", {
        "section": section,
        "rows": rows,
        "page_obj": page_obj,
        "q": query,
        "current_url": request.get_full_path(),
    }, active=section.key)


@staff_required
def section_form(request, key, pk=None):
    section = get_section(key)
    instance = get_object_or_404(section.model, pk=pk) if pk else None
    Form = build_form_class(section.model, section.fields)

    if request.method == "POST":
        form = Form(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save()
            if section.has_gallery and instance is None:
                # Stay on the page so the gallery photos can be added next
                messages.success(request, f"{section.singular} “{obj}” saved. You can now add gallery photos.")
                return redirect("dashboard:edit", key=key, pk=obj.pk)
            messages.success(request, f"{section.singular} “{obj}” saved.")
            return redirect("dashboard:list", key=key)
    else:
        form = Form(instance=instance)

    context = {"section": section, "form": form, "instance": instance, "max_image_mb": MAX_IMAGE_MB}
    if section.has_gallery and instance is not None:
        context["gallery"] = instance.images.order_by("id")

    return page(request, "dashboard/form.html", context, active=section.key)


@staff_required
def section_delete(request, key, pk):
    section = get_section(key)
    obj = get_object_or_404(section.model, pk=pk)

    if request.method == "POST":
        try:
            obj.delete()
        except ProtectedError:
            messages.error(
                request,
                f"“{obj}” cannot be deleted because other records still use it "
                "(for example products in this category, or past orders).",
            )
            return redirect("dashboard:list", key=key)
        messages.success(request, f"{section.singular} “{obj}” deleted.")
        return redirect("dashboard:list", key=key)

    return page(request, "dashboard/confirm_delete.html", {"section": section, "obj": obj}, active=section.key)


@staff_required
@require_POST
def section_toggle(request, key, pk):
    """Flip a yes/no field (shown, available, published) without opening the form."""
    section = get_section(key)
    if not section.toggle_field:
        raise Http404("This section has no show/hide switch")

    obj = get_object_or_404(section.model, pk=pk)
    new_value = not getattr(obj, section.toggle_field)
    setattr(obj, section.toggle_field, new_value)
    obj.save(update_fields=[section.toggle_field])

    messages.success(request, f"“{obj}” is now {'visible' if new_value else 'hidden'}.")
    return redirect(safe_next(request, reverse("dashboard:list", args=[key])))


# ---------------------------------------------------------------------------
# Project gallery
# ---------------------------------------------------------------------------

@staff_required
@require_POST
def gallery_add(request, pk):
    project = get_object_or_404(Project, pk=pk)
    files = request.FILES.getlist("images")
    back = redirect("dashboard:edit", key="projects", pk=project.pk)

    if not files:
        messages.warning(request, "Choose at least one photo first.")
        return back

    checker = forms.ImageField()  # confirms each file really is an image
    added, problems = 0, []
    for upload in files:
        try:
            checker.clean(upload)
            validate_image_size(upload)
        except ValidationError as error:
            problems.append(f"{upload.name}: {error.messages[0]}")
            continue
        ProjectImage.objects.create(project=project, image=upload)
        added += 1

    if added:
        messages.success(request, f"{added} photo{'s' if added != 1 else ''} added to the gallery.")
    for problem in problems:
        messages.error(request, problem)
    return back


@staff_required
@require_POST
def gallery_delete(request, pk, image_pk):
    image = get_object_or_404(ProjectImage, pk=image_pk, project_id=pk)
    image.image.delete(save=False)  # remove the file from storage too
    image.delete()
    messages.success(request, "Photo removed from the gallery.")
    return redirect("dashboard:edit", key="projects", pk=pk)