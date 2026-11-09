from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html

from . import i18n

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


class TrixWidget(forms.Widget):
    """Rich-text editor (bold, headings, lists, links, quotes) built on Trix.

    It renders a hidden input, which Django reads, plus the editor box that fills it.
    The Trix files are loaded in templates/dashboard/base.html.
    """

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        field_id = attrs.get("id") or f"id_{name}"
        return format_html(
            '<input type="hidden" name="{}" id="{}" value="{}">'
            '<trix-editor input="{}" class="form-control trix-box"></trix-editor>',
            name, field_id, "" if value is None else value, field_id,
        )


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

            field.label = i18n.clean_label(field.label)  # "Name [en]" -> "Name"

        # Translated fields: the default language is required when the original field is,
        # every other language is optional (visitors then see the default language).
        model = self._meta.model
        default_code = i18n.default_language()
        for name in i18n.translated_names(model):
            if not model._meta.get_field(name).blank:
                field = self.fields.get(i18n.localized_name(name, default_code))
                if field is not None:
                    field.required = True
                    field.widget.is_required = True


def build_form_class(model, fields, rich_fields=()):
    """Create a form for the given model and field names.

    Translated fields are replaced by one field per language. Fields listed in
    rich_fields use the rich-text editor instead of a plain box.
    """
    names = i18n.expand(model, fields)
    widgets = {name: TrixWidget() for name in i18n.expand(model, rich_fields)}
    return forms.modelform_factory(
        model, form=StyledModelForm, fields=names,
        widgets=widgets, formfield_callback=_formfield,
    )


def build_tabs(form, model, fields):
    """
    Arrange a form into tabs: General (fields that are not translated), then one tab
    per language. With no translated fields there is a single General tab.
    """
    translated = i18n.translated_names(model)

    general = [form[name] for name in fields if name not in translated]
    tabs = []
    if general:
        tabs.append({"id": "tab-general", "title": "General", "icon": "bi-sliders", "fields": general})

    if translated:
        default_code = i18n.default_language()
        default_label = dict(i18n.languages()).get(default_code, default_code)
        for code, label in i18n.languages():
            tabs.append({
                "id": f"tab-{code}",
                "title": label,
                "icon": "bi-translate",
                "hint": "" if code == default_code else
                        f"Optional. Anything left empty is shown to visitors in {default_label}.",
                "fields": [form[i18n.localized_name(name, code)] for name in fields if name in translated],
            })

    for tab in tabs:
        tab["has_errors"] = any(field.errors for field in tab["fields"])

    # Open the first tab that has an error, otherwise the first tab
    active = next((tab["id"] for tab in tabs if tab["has_errors"]), tabs[0]["id"])
    for tab in tabs:
        tab["active"] = tab["id"] == active
    return tabs
