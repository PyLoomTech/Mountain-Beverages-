from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("site-content/", views.site_content, name="site"),

    # Project gallery
    path("projects/<int:pk>/gallery/add/", views.gallery_add, name="gallery_add"),
    path("projects/<int:pk>/gallery/<int:image_pk>/delete/", views.gallery_delete, name="gallery_delete"),

    # Generic screens for every section in registry.py
    path("<slug:key>/", views.section_list, name="list"),
    path("<slug:key>/new/", views.section_form, name="new"),
    path("<slug:key>/<int:pk>/edit/", views.section_form, name="edit"),
    path("<slug:key>/<int:pk>/delete/", views.section_delete, name="delete"),
    path("<slug:key>/<int:pk>/toggle/", views.section_toggle, name="toggle"),
]