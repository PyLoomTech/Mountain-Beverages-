from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Announcement, Highlight, TeamMember

# ---------------------------------------------------------------------------
# SAMPLE CONTENT: replace with the client's real information from the admin.
# ---------------------------------------------------------------------------

HIGHLIGHTS = [
    # icon, value, title, description
    ("bi-droplet-fill", "100%", "Pure Natural Water", "Sourced from natural mountain springs."),
    ("bi-shield-check", "", "Quality Tested", "Every batch is checked for safety and purity."),
    ("bi-truck", "", "Reliable Delivery", "On-time delivery for homes, offices and events."),
    ("bi-people-fill", "", "Trusted by Customers", "Serving homes, hotels and businesses across Nepal."),
]

TEAM = [
    # name, position, bio
    ("Sample Member 1", "Managing Director",
     "Sample biography. Replace with the real profile from the client."),
    ("Sample Member 2", "Operations Manager",
     "Sample biography. Replace with the real profile from the client."),
    ("Sample Member 3", "Sales and Marketing Manager",
     "Sample biography. Replace with the real profile from the client."),
    ("Sample Member 4", "Quality Control Officer",
     "Sample biography. Replace with the real profile from the client."),
]


class Command(BaseCommand):
    help = "Add sample highlights, team members and an announcement (only to empty tables)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not Highlight.objects.exists():
            for order, (icon, value, title, description) in enumerate(HIGHLIGHTS, start=1):
                Highlight.objects.create(
                    icon=icon, value=value, title=title, description=description, order=order
                )
            self.stdout.write("Highlights: added")
        else:
            self.stdout.write("Highlights: already have data, skipped")

        if not TeamMember.objects.exists():
            for order, (name, position, bio) in enumerate(TEAM, start=1):
                TeamMember.objects.create(name=name, position=position, bio=bio, order=order)
            self.stdout.write("Team members: added")
        else:
            self.stdout.write("Team members: already have data, skipped")

        if not Announcement.objects.exists():
            Announcement.objects.create(
                title="Welcome to Mountain Beverage Group",
                message=(
                    "Order pure natural water online and get it delivered to your door.\n"
                    "(Sample announcement. Edit it in the admin under Announcements.)"
                ),
                button_text="Browse Products",
                button_url="/products/",
            )
            self.stdout.write("Announcement: added")
        else:
            self.stdout.write("Announcement: already has data, skipped")

        self.stdout.write(self.style.SUCCESS("Sample content is ready."))