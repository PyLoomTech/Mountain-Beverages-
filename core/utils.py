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