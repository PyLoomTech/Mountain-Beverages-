from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Category, Product
from core.models import Announcement, Highlight, SiteSettings, TeamMember
from projects.models import Project

# ---------------------------------------------------------------------------
# SAMPLE NEPALI TEXT. It is a first draft for the demo: have a native speaker
# review it, and replace it with the client's own wording from the dashboard.
# The command only fills Nepali fields that are still empty (or still a copy of
# the English text), so it never overwrites text that staff have written.
# ---------------------------------------------------------------------------

SITE = {
    "company_name": "माउन्टेन बेभरेज ग्रुप",
    "tagline": "पानी बचाऔँ, जीवन बचाऔँ",
    "hero_title": "पानीको एक थोपाले पनि जीवन बचाउन सक्छ",
    "hero_subtitle": "हिमालको काखबाट आएको शुद्ध प्राकृतिक पानी, तपाईंको घरसम्म।",
    "about_text": (
        "माउन्टेन बेभरेज ग्रुपले नेपालभरका घर, कार्यालय, होटल तथा कार्यक्रमहरूमा शुद्ध प्राकृतिक "
        "पिउने पानी र ताजगी दिने पेय पदार्थ पुर्याउँछ। हामी स्वच्छ पानी सबैको आधारभूत अधिकार हो "
        "भन्ने विश्वास गर्छौं र यसलाई सावधानीपूर्वक पुर्याउन प्रतिबद्ध छौं।\n\n"
        "(नमुना पाठ। ग्राहकबाट प्राप्त कम्पनी परिचयले प्रतिस्थापन गर्नुहोस्।)"
    ),
    "history": "नमुना पाठ। ग्राहकबाट प्राप्त कम्पनीको इतिहासले प्रतिस्थापन गर्नुहोस्।",
    "vision": "नेपालमा शुद्ध प्राकृतिक पानीको सबैभन्दा विश्वसनीय स्रोत बन्नु।",
    "mission": "हाम्रा प्राकृतिक स्रोतहरूको संरक्षण गर्दै सुरक्षित र उच्च गुणस्तरको पानी तथा पेय पदार्थ उपलब्ध गराउनु।",
    "core_values": "शुद्धता\nगुणस्तर\nइमानदारी\nदिगोपन\nग्राहक सन्तुष्टि",
    "address": "नेपाल (नमुना ठेगाना)",
    "business_hours": "आइतबार - शुक्रबार, बिहान ९:०० - साँझ ६:००",
}

CATEGORIES = {
    "Packaged Drinking Water": "प्याकेजिङ गरिएको पिउने पानी",
    "Other Beverages": "अन्य पेय पदार्थ",
}

# English name -> (Nepali name, Nepali short description)
PRODUCTS = {
    "Pure Natural Water 500 ml": (
        "शुद्ध प्राकृतिक पानी ५०० मि.ली.", "सजिलै बोक्न मिल्ने ५०० मि.ली. बोतलमा शुद्ध प्राकृतिक पहाडी पानी।"),
    "Pure Natural Water 1 L": (
        "शुद्ध प्राकृतिक पानी १ लिटर", "घर र कार्यालयका लागि दैनिक प्रयोगको १ लिटरको बोतल।"),
    "Pure Natural Water 20 L Jar": (
        "शुद्ध प्राकृतिक पानी २० लिटर जार", "घर, कार्यालय र कार्यक्रमका लागि ठूलो पुनः भर्न मिल्ने जार।"),
    "Pure Natural Water 500 ml Carton (24 bottles)": (
        "शुद्ध प्राकृतिक पानी ५०० मि.ली. कार्टुन (२४ बोतल)", "२४ बोतलको पूरा कार्टुन, कार्यक्रम र पसलका लागि उपयुक्त।"),
    "Pure Natural Water 1 L Pack (12 bottles)": (
        "शुद्ध प्राकृतिक पानी १ लिटर प्याक (१२ बोतल)", "सजिलो प्याकमा १२ वटा १ लिटरका बोतल।"),
    "Mixed Fruit Juice 250 ml": (
        "मिश्रित फलफूल जुस २५० मि.ली.", "विभिन्न फलफूलको स्वादको ताजगी दिने मिश्रण।"),
    "Mango Drink 250 ml": (
        "आमको पेय २५० मि.ली.", "मिठो र चिसो आमको पेय।"),
}

UNITS = {"bottle": "बोतल", "jar": "जार", "carton": "कार्टुन", "pack": "प्याक"}

# English title -> (Nepali title, Nepali description)
HIGHLIGHTS = {
    "Pure Natural Water": ("शुद्ध प्राकृतिक पानी", "प्राकृतिक पहाडी मूलबाट प्राप्त।", "१००%"),
    "Quality Tested": ("गुणस्तर परीक्षण गरिएको", "प्रत्येक ब्याचको सुरक्षा र शुद्धता जाँच गरिन्छ।", ""),
    "Reliable Delivery": ("भरपर्दो डेलिभरी", "घर, कार्यालय र कार्यक्रममा समयमै डेलिभरी।", ""),
    "Trusted by Customers": ("ग्राहकको विश्वास", "नेपालभरका घर, होटल र व्यवसायलाई सेवा।", ""),
}

# English name -> (Nepali name, Nepali position)
TEAM = {
    "Sample Member 1": ("नमुना सदस्य १", "व्यवस्थापकीय निर्देशक"),
    "Sample Member 2": ("नमुना सदस्य २", "सञ्चालन प्रबन्धक"),
    "Sample Member 3": ("नमुना सदस्य ३", "बिक्री तथा मार्केटिङ प्रबन्धक"),
    "Sample Member 4": ("नमुना सदस्य ४", "गुणस्तर नियन्त्रण अधिकृत"),
}
TEAM_BIO = "नमुना परिचय। ग्राहकबाट प्राप्त वास्तविक विवरणले प्रतिस्थापन गर्नुहोस्।"

# English title -> (Nepali title, Nepali category, Nepali description)
PROJECTS = {
    "Corporate Event Water Supply": (
        "कर्पोरेट कार्यक्रमका लागि पानी आपूर्ति", "आपूर्ति",
        "तीन दिने कर्पोरेट सम्मेलनका लागि ब्रान्डेड बोतल र स्थलमै डेलिभरीसहित शुद्ध पिउने पानी आपूर्ति गरियो। (नमुना परियोजना पाठ।)"),
    "Hotel and Restaurant Partnership": (
        "होटल तथा रेस्टुरेन्ट साझेदारी", "साझेदारी",
        "स्थानीय होटल तथा रेस्टुरेन्टसँग साप्ताहिक तालिकाअनुसार डेलिभरी हुने नियमित आपूर्ति साझेदारी सुरु गरियो। (नमुना परियोजना पाठ।)"),
    "Community Clean Water Campaign": (
        "सामुदायिक स्वच्छ पानी अभियान", "सामुदायिक",
        "'पानी बचाऔँ, जीवन बचाऔँ' सन्देशअन्तर्गत पानी संरक्षणबारे सामुदायिक चेतना अभियान। (नमुना परियोजना पाठ।)"),
}

ANNOUNCEMENT = {
    "title": "माउन्टेन बेभरेज ग्रुपमा स्वागत छ",
    "message": (
        "शुद्ध प्राकृतिक पानी अनलाइन अर्डर गर्नुहोस् र तपाईंको घरमै मगाउनुहोस्।\n"
        "(नमुना घोषणा। ड्यासबोर्डको घोषणा खण्डबाट सम्पादन गर्नुहोस्।)"
    ),
    "button_text": "उत्पादनहरू हेर्नुहोस्",
}


def fill(obj, **values):
    """
    Set the Nepali version of each field that is not translated yet. Returns True if anything changed.

    A field counts as "not translated yet" when the Nepali value is empty or still the same
    as the English one (fields with a default value, such as the unit "bottle", start out that way).
    """
    changed = False
    for field, text in values.items():
        current = getattr(obj, f"{field}_ne")
        if text and (not current or current == getattr(obj, f"{field}_en")):
            setattr(obj, f"{field}_ne", text)
            changed = True
    if changed:
        obj.save()
    return changed


class Command(BaseCommand):
    help = "Add sample Nepali text next to the sample English content (only where Nepali is still empty)."

    @transaction.atomic
    def handle(self, *args, **options):
        updated = 0

        updated += fill(SiteSettings.load(), **SITE)

        for obj in Category.objects.all():
            updated += fill(obj, name=CATEGORIES.get(obj.name_en))

        for obj in Product.objects.all():
            name, short = PRODUCTS.get(obj.name_en, ("", ""))
            updated += fill(obj, name=name, short_description=short, description=short,
                            unit=UNITS.get(obj.unit_en))

        for obj in Highlight.objects.all():
            title, description, value = HIGHLIGHTS.get(obj.title_en, ("", "", ""))
            updated += fill(obj, title=title, description=description, value=value)

        for obj in TeamMember.objects.all():
            name, position = TEAM.get(obj.name_en, ("", ""))
            updated += fill(obj, name=name, position=position, bio=TEAM_BIO if name else "")

        for obj in Project.objects.all():
            title, category, description = PROJECTS.get(obj.title_en, ("", "", ""))
            updated += fill(obj, title=title, category=category, description=description)

        for obj in Announcement.objects.filter(title_en="Welcome to Mountain Beverage Group"):
            updated += fill(obj, **ANNOUNCEMENT)

        self.stdout.write(self.style.SUCCESS(f"Nepali sample text added to {updated} item(s)."))
        self.stdout.write("Have a Nepali speaker review it before the client sees it.")
