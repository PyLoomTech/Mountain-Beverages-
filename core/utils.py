import html as html_lib
import re

import nh3
from django.utils.text import slugify


def unique_slug(instance, source_value, slug_field="slug"):
    """
    Build a slug from source_value that is not used by any other row of the
    same model. "Mango Drink" becomes "mango-drink", and a second product with
    the same name becomes "mango-drink-2", so saving never fails on a clash.
    """
    model = instance.__class__
    max_length = model._meta.get_field(slug_field).max_length

    # Leave room for a "-123" suffix
    base = slugify(source_value)[: max_length - 6] or model._meta.model_name
    slug = base
    counter = 2

    others = model._default_manager.all()
    if instance.pk:
        others = others.exclude(pk=instance.pk)

    while others.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ---------------------------------------------------------------------------
# Safe HTML for rich-text content (posts)
# ---------------------------------------------------------------------------

ALLOWED_TAGS = {
    "p", "div", "br", "strong", "b", "em", "i", "del", "a",
    "ul", "ol", "li", "blockquote", "pre", "code", "h2", "h3", "h4",
}
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}
ALLOWED_SCHEMES = {"http", "https", "mailto", "tel"}


def clean_html(html):
    """
    Make editor HTML safe to show to visitors.

    Keeps simple formatting (bold, lists, links, headings, quotes) and removes
    everything else: scripts, event handlers such as onclick, iframes, images,
    styles and unsafe links like javascript:. Links get rel="noopener noreferrer".
    The editor's single heading level (h1) becomes h2, because the page title is
    already the h1.
    """
    if not html:
        return ""
    html = re.sub(r"<(/?)h1\b", r"<\1h2", html, flags=re.IGNORECASE)
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
        link_rel="noopener noreferrer",
    ).strip()


def plain_text(html):
    """Editor HTML as plain text (used for short previews)."""
    from django.utils.html import strip_tags

    return html_lib.unescape(strip_tags(html or "")).strip()