from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Category, Product
from core.models import SiteSettings
from orders.models import Order, OrderItem
from projects.models import Project
from reviews.models import Review

User = get_user_model()

DEMO_PASSWORD = "demo12345"

# ---------------------------------------------------------------------------
# SAMPLE CONTENT: replace with the client's real information before launch.
# ---------------------------------------------------------------------------

SITE_DEFAULTS = {
    "tagline": "Save Water Save Life",
    "hero_title": "One Drop of Water, Can Save Life",
    "hero_subtitle": "Pure natural water from the heart of the Himalayas, delivered to your door.",
    "about_text": (
        "Mountain Beverage Group brings pure, natural drinking water and refreshing "
        "beverages to homes, offices, hotels and events across Nepal. We believe clean "
        "water is a basic right, and we are committed to delivering it with care.\n\n"
        "(Sample text. Replace with the company introduction from the client.)"
    ),
    "history": "Sample text. Replace with the company history from the client.",
    "vision": "To be the most trusted source of pure natural water in Nepal.",
    "mission": "To deliver safe, high-quality water and beverages while protecting our natural resources.",
    "core_values": "Purity\nQuality\nIntegrity\nSustainability\nCustomer satisfaction",
    "address": "Nepal (sample address)",
    "phone": "+977-9800000000",
    "email": "info@example.com",
    "business_hours": "Sun - Fri, 9:00 AM - 6:00 PM",
}

CATEGORIES = ["Packaged Drinking Water", "Other Beverages"]

PRODUCTS = [
    # name, category, price (NPR), unit, featured, short description, specifications
    ("Pure Natural Water 500 ml", "Packaged Drinking Water", "15.00", "bottle", True,
     "Pure natural mountain water in a handy 500 ml bottle.",
     "Volume: 500 ml\nSource: Natural mountain spring\nPackaging: PET bottle"),
    ("Pure Natural Water 1 L", "Packaged Drinking Water", "25.00", "bottle", True,
     "Our everyday 1 litre bottle for home and office.",
     "Volume: 1 litre\nSource: Natural mountain spring\nPackaging: PET bottle"),
    ("Pure Natural Water 20 L Jar", "Packaged Drinking Water", "150.00", "jar", True,
     "Large refillable jar for homes, offices and events.",
     "Volume: 20 litres\nPackaging: Reusable jar\nBest for: Offices, hotels, events"),
    ("Pure Natural Water 500 ml Carton (24 bottles)", "Packaged Drinking Water", "340.00", "carton", False,
     "A full carton of 24 bottles, ideal for events and shops.",
     "Contents: 24 x 500 ml\nPackaging: Shrink-wrapped carton"),
    ("Pure Natural Water 1 L Pack (12 bottles)", "Packaged Drinking Water", "270.00", "pack", False,
     "Twelve 1 litre bottles in one convenient pack.",
     "Contents: 12 x 1 litre\nPackaging: Shrink-wrapped pack"),
    ("Mixed Fruit Juice 250 ml", "Other Beverages", "35.00", "bottle", True,
     "A refreshing blend of fruit flavours.",
     "Volume: 250 ml\nFlavour: Mixed fruit"),
    ("Mango Drink 250 ml", "Other Beverages", "30.00", "bottle", False,
     "Sweet and cool mango drink.",
     "Volume: 250 ml\nFlavour: Mango"),
]

PROJECTS = [
    ("Corporate Event Water Supply", "Supply", date(2026, 5, 12), True,
     "Supplied pure drinking water for a three-day corporate conference, including "
     "branded bottles and on-site delivery. (Sample project text.)"),
    ("Hotel and Restaurant Partnership", "Partnership", date(2026, 3, 20), True,
     "Started a regular supply partnership with local hotels and restaurants, "
     "with scheduled weekly deliveries. (Sample project text.)"),
    ("Community Clean Water Campaign", "Community", date(2026, 1, 15), True,
     "A community awareness campaign about water conservation under our "
     "'Save Water Save Life' message. (Sample project text.)"),
]

# username, first, last, phone, address
CUSTOMERS = [
    ("demo_customer", "Demo", "Customer", "9800000001", "Demo Street, Nepal"),
    ("sita_sharma", "Sita", "Sharma", "9800000002", "Sample Tole, Nepal"),
    ("hari_thapa", "Hari", "Thapa", "9800000003", "Sample Chowk, Nepal"),
    ("anita_gurung", "Anita", "Gurung", "9800000004", "Sample Marg, Nepal"),
    ("bikash_rai", "Bikash", "Rai", "9800000005", "Sample Nagar, Nepal"),
]

# username -> (order status, [(product name, quantity), ...])
ORDERS = {
    "sita_sharma": ("delivered", [("Pure Natural Water 20 L Jar", 2), ("Pure Natural Water 1 L", 6)]),
    "bikash_rai": ("delivered", [("Pure Natural Water 500 ml Carton (24 bottles)", 3)]),
    "hari_thapa": ("confirmed", [("Pure Natural Water 1 L Pack (12 bottles)", 4)]),
    "anita_gurung": ("pending", [("Mixed Fruit Juice 250 ml", 12), ("Pure Natural Water 500 ml", 10)]),
}

# username -> (rating, comment, status). The demo customer gets no review on
# purpose, so you can show the full order -> delivered -> review flow live.
REVIEWS = {
    "sita_sharma": (5, "Very pure and fresh water. Delivery was on time and the jars were clean. Highly recommended!", "approved"),
    "anita_gurung": (5, "We order for our office every week. Reliable service and great taste.", "approved"),
    "hari_thapa": (4, "Good quality water at a fair price. The ordering process was simple.", "approved"),
    "bikash_rai": (4, "Ordered cartons for our event. Everything arrived in perfect condition.", "pending"),
}


class Command(BaseCommand):
    help = "Fill the database with sample data for the prototype demo (safe to run more than once)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.seed_site()
        products = self.seed_catalog()
        self.seed_projects()
        users = self.seed_customers()
        self.seed_orders(users, products)
        self.seed_reviews(users)

        self.stdout.write(self.style.SUCCESS("\nDemo data is ready."))
        self.stdout.write(f"Demo customer login:  demo_customer / {DEMO_PASSWORD}")
        self.stdout.write("Other sample customers use the same password.")
        self.stdout.write("Admin login: the superuser you created earlier.")

    # -- site settings (fills blank fields only, never overwrites your edits) --
    def seed_site(self):
        site = SiteSettings.load()
        for field, value in SITE_DEFAULTS.items():
            if not getattr(site, field):
                setattr(site, field, value)
        site.save()
        self.stdout.write("Site settings: ok")

    # -- categories and products --
    def seed_catalog(self):
        categories = {}
        for name in CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(name=name)

        products = {}
        for name, cat, price, unit, featured, short, specs in PRODUCTS:
            product, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": categories[cat],
                    "price": price,
                    "unit": unit,
                    "is_featured": featured,
                    "is_available": True,
                    "short_description": short,
                    "description": short,
                    "specifications": specs,
                },
            )
            products[name] = product
        self.stdout.write(f"Products: {len(products)} ready")
        return products

    # -- projects --
    def seed_projects(self):
        for title, category, when, featured, description in PROJECTS:
            Project.objects.get_or_create(
                title=title,
                defaults={
                    "category": category,
                    "date": when,
                    "is_featured": featured,
                    "is_published": True,
                    "description": description,
                },
            )
        self.stdout.write(f"Projects: {len(PROJECTS)} ready")

    # -- customers --
    def seed_customers(self):
        users = {}
        for username, first, last, phone, address in CUSTOMERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@example.com",
                    "phone": phone,
                    "address": address,
                    "role": "customer",
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[username] = user
        self.stdout.write(f"Customers: {len(users)} ready")
        return users

    # -- orders (only for customers that have none yet) --
    def seed_orders(self, users, products):
        for username, (status, lines) in ORDERS.items():
            user = users[username]
            if Order.objects.filter(customer=user).exists():
                continue
            order = Order.objects.create(
                customer=user,
                status=status,
                full_name=user.get_full_name(),
                phone=user.phone,
                address=user.address,
            )
            for product_name, quantity in lines:
                product = products[product_name]
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=product.price,
                )
        self.stdout.write("Orders: ready")

    # -- reviews (get_or_create so approvals you make later are kept) --
    def seed_reviews(self, users):
        for username, (rating, comment, status) in REVIEWS.items():
            Review.objects.get_or_create(
                customer=users[username],
                defaults={"rating": rating, "comment": comment, "status": status},
            )
        self.stdout.write("Reviews: ready")
        