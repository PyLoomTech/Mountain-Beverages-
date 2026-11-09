from modeltranslation.translator import TranslationOptions, register

from .models import Post


@register(Post)
class PostTranslation(TranslationOptions):
    fields = ("title", "summary", "content")
