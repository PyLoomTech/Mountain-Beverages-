from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Addresses without a language: the staff panel and the language switcher
urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", include("dashboard.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
]

# The public website: /en/... in English and /ne/... in Nepali
urlpatterns += i18n_patterns(
    path("accounts/", include("accounts.urls")),
    path("", include("core.urls")),
    path("", include("catalog.urls")),
    path("", include("projects.urls")),
    path("", include("posts.urls")),
    path("", include("orders.urls")),
    path("", include("reviews.urls")),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
