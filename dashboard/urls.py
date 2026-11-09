from django.urls import path

from . import ops_views, views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("site-content/", views.site_content, name="site"),

    # Orders
    path("orders/", ops_views.orders_list, name="orders"),
    path("orders/<int:pk>/", ops_views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", ops_views.order_status, name="order_status"),

    # Reviews
    path("reviews/", ops_views.reviews_list, name="reviews"),
    path("reviews/<int:pk>/status/", ops_views.review_status, name="review_status"),
    path("reviews/<int:pk>/delete/", ops_views.review_delete, name="review_delete"),

    # Contact messages
    path("messages/", ops_views.inbox, name="inbox"),
    path("messages/<int:pk>/", ops_views.message_detail, name="message_detail"),
    path("messages/<int:pk>/unread/", ops_views.message_unread, name="message_unread"),
    path("messages/<int:pk>/delete/", ops_views.message_delete, name="message_delete"),

    # Customers
    path("customers/", ops_views.customers_list, name="customers"),
    path("customers/<int:pk>/", ops_views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/active/", ops_views.customer_active, name="customer_active"),

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
