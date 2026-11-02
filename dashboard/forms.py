from django import forms
from django.core.exceptions import ValidationError
from django.db import models

MAX_IMAGE_MB = 5


def validate_image_size(file):
    if file.size > MAX_IMAGE_MB * 1024 * 1024:
        raise ValidationError(f"This image is too large. The maximum size is {MAX_IMAGE_MB} MB.")


def _formfield(db_field, **kwargs):
    """Give date fields a proper date picker (DateTimeField is a kind of DateField, so check it first)."""
    if isinstance(db_field, models.DateTimeField):
        kwargs["widget"] = forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
        kwargs["input_formats"] = ["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"]
    elif isinstance(db_field, models.DateField):
        kwargs["widget"] = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    return db_field.formfield(**kwargs)


class StyledModelForm(forms.ModelForm):
    """A ModelForm whose fields use Bootstrap styling and limit image size."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
                # "Is active" reads better as "Active"
                if field.label and field.label.startswith("Is "):
                    field.label = field.label[3:].capitalize()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 4)
            if isinstance(field, forms.ImageField):
                field.validators.append(validate_image_size)
                widget.attrs["accept"] = "image/*"


def build_form_class(model, fields):
    """Create a form for the given model and field names."""
    return forms.modelform_factory(
        model, form=StyledModelForm, fields=list(fields), formfield_callback=_formfield
    )