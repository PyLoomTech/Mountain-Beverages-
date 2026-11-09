from modeltranslation.translator import TranslationOptions, register

from .models import Announcement, Highlight, SiteSettings, TeamMember


@register(SiteSettings)
class SiteSettingsTranslation(TranslationOptions):
    fields = (
        "company_name", "tagline", "hero_title", "hero_subtitle",
        "about_text", "history", "vision", "mission", "core_values",
        "address", "business_hours",
    )


@register(Announcement)
class AnnouncementTranslation(TranslationOptions):
    fields = ("title", "message", "button_text")


@register(Highlight)
class HighlightTranslation(TranslationOptions):
    fields = ("value", "title", "description")


@register(TeamMember)
class TeamMemberTranslation(TranslationOptions):
    fields = ("name", "position", "bio")
