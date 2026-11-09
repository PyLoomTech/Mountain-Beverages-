from django.utils import translation


class StaffPanelInEnglishMiddleware:
    """
    The dashboard and the Django admin are English only. Without this, a staff
    member whose browser is set to Nepali (or who last switched the public site
    to Nepali) would see Nepali text mixed into the English panel, and saving a
    product could build its web address from the Nepali name.
    """

    PREFIXES = ("/dashboard/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith(self.PREFIXES):
            translation.activate("en")
            request.LANGUAGE_CODE = "en"
        return self.get_response(request)
