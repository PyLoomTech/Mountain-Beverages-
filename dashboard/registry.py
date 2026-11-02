"""
The dashboard is driven by this list.

Each Section describes one kind of content: which model it edits, which fields
appear in the form, and which columns appear in the list. To manage a new kind
of content later (posts, for example), add one Section here.
"""
from dataclasses import dataclass

from catalog.models import Category, Product
from core.models import Announcement, Highlight, TeamMember
from projects.models import Project


@dataclass(frozen=True)
class Column:
    label: str
    attr: str          # field, property or "relation.method" such as "products.count"
    kind: str = "text"  # text | image | bool | date | datetime | money | icon


@dataclass(frozen=True)
class Section:
    key: str            # used in the URL: /dashboard/<key>/
    group: str          # heading in the sidebar
    label: str          # plural name, e.g. "Products"
    singular: str       # e.g. "Product"
    icon: str           # Bootstrap icon class
    model: type
    fields: tuple       # fields shown in the add/edit form
    columns: tuple      # columns shown in the list
    search_fields: tuple = ()
    toggle_field: str = ""   # yes/no field flipped by the Show/Hide button
    has_gallery: bool = False
    help_text: str = ""


_SECTIONS = (
    Section(
        key="announcements", group="Home page", label="Announcements", singular="Announcement",
        icon="bi-megaphone", model=Announcement,
        fields=("title", "message", "image", "button_text", "button_url",
                "start_at", "end_at", "is_active"),
        columns=(
            Column("Title", "title"),
            Column("Live now", "is_live", "bool"),
            Column("Starts", "start_at", "datetime"),
            Column("Ends", "end_at", "datetime"),
        ),
        search_fields=("title", "message"), toggle_field="is_active",
        help_text="The pop-up on the home page. The newest live announcement is shown.",
    ),
    Section(
        key="highlights", group="Home page", label="Highlights", singular="Highlight",
        icon="bi-stars", model=Highlight,
        fields=("icon", "value", "title", "description", "order", "is_active"),
        columns=(
            Column("Order", "order"),
            Column("Icon", "icon", "icon"),
            Column("Title", "title"),
            Column("Big text", "value"),
            Column("Shown", "is_active", "bool"),
        ),
        search_fields=("title", "description"), toggle_field="is_active",
        help_text="The company highlight cards under the home page banner.",
    ),
    Section(
        key="team", group="About page", label="Team members", singular="Team member",
        icon="bi-people", model=TeamMember,
        fields=("name", "position", "photo", "bio", "facebook_url", "linkedin_url",
                "order", "is_active"),
        columns=(
            Column("Photo", "photo", "image"),
            Column("Name", "name"),
            Column("Position", "position"),
            Column("Order", "order"),
            Column("Shown", "is_active", "bool"),
        ),
        search_fields=("name", "position"), toggle_field="is_active",
        help_text="People shown in the Our Team section of the About page.",
    ),
    Section(
        key="categories", group="Catalog", label="Categories", singular="Category",
        icon="bi-tags", model=Category,
        fields=("name",),
        columns=(
            Column("Name", "name"),
            Column("Products", "products.count"),
        ),
        search_fields=("name",),
        help_text="Product categories used for filtering on the Products page.",
    ),
    Section(
        key="products", group="Catalog", label="Products", singular="Product",
        icon="bi-box-seam", model=Product,
        fields=("category", "name", "image", "short_description", "description",
                "specifications", "price", "unit", "is_available", "is_featured"),
        columns=(
            Column("Image", "image", "image"),
            Column("Name", "name"),
            Column("Category", "category"),
            Column("Price", "price", "money"),
            Column("Available", "is_available", "bool"),
            Column("Featured", "is_featured", "bool"),
        ),
        search_fields=("name", "description"), toggle_field="is_available",
        help_text="Products customers can order.",
    ),
    Section(
        key="projects", group="Projects", label="Projects", singular="Project",
        icon="bi-kanban", model=Project,
        fields=("title", "category", "description", "date", "cover_image",
                "is_published", "is_featured"),
        columns=(
            Column("Cover", "cover_image", "image"),
            Column("Title", "title"),
            Column("Category", "category"),
            Column("Date", "date", "date"),
            Column("Published", "is_published", "bool"),
            Column("Featured", "is_featured", "bool"),
        ),
        search_fields=("title", "description"), toggle_field="is_published", has_gallery=True,
        help_text="Company projects. Add gallery photos after saving a project.",
    ),
)

SECTIONS = {section.key: section for section in _SECTIONS}

# Sidebar: heading -> sections under it
NAV_GROUPS = {}
for _section in _SECTIONS:
    NAV_GROUPS.setdefault(_section.group, []).append(_section)

# The one-page "Site content" screen (company text, banner, contact, social links)
SITE_GROUPS = (
    ("General and banner", "bi-house",
     ("company_name", "tagline", "hero_title", "hero_subtitle", "hero_image")),
    ("About page", "bi-info-circle",
     ("about_text", "history", "vision", "mission", "core_values")),
    ("Contact and social", "bi-telephone",
     ("address", "phone", "email", "business_hours", "map_embed_url",
      "facebook_url", "instagram_url", "whatsapp_number")),
)

SITE_FIELDS = tuple(name for _, _, names in SITE_GROUPS for name in names)