from modeltranslation.translator import TranslationOptions, register

from .models import Project


@register(Project)
class ProjectTranslation(TranslationOptions):
    fields = ("title", "category", "description")
