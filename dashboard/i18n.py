"""
Helpers for editing content in more than one language.

When django-modeltranslation is installed and a model is registered with it, each
translated field (for example "name") has one real field per language
("name_en", "name_ne"). The helpers below let the dashboard forms handle that
without every view knowing about it. If modeltranslation is not installed, they
simply report that nothing is translated.
"""
import re

from django.conf import settings

try:
    from modeltranslation.settings import DEFAULT_LANGUAGE
    from modeltranslation.translator import NotRegistered, translator
    from modeltranslation.utils import build_localized_fieldname
except ImportError:  # modeltranslation not installed: everything is single-language
    translator = None

LABEL_SUFFIX = re.compile(r"\s*\[[A-Za-z_-]+\]$")  # "Name [en]" -> "Name"


def languages():
    """[("en", "English"), ("ne", "नेपाली")]"""
    return list(settings.LANGUAGES)


def default_language():
    if translator is None:
        return settings.LANGUAGE_CODE.split("-")[0]
    return DEFAULT_LANGUAGE


def translated_names(model):
    """Names of the fields of this model that are translated (empty if none)."""
    if translator is None:
        return set()
    try:
        return set(translator.get_options_for_model(model).all_fields)
    except NotRegistered:
        return set()


def localized_name(field_name, code):
    return build_localized_fieldname(field_name, code)


def expand(model, names):
    """Replace each translated field name by its per-language field names."""
    translated = translated_names(model)
    result = []
    for name in names:
        if name in translated:
            result.extend(localized_name(name, code) for code, _ in languages())
        else:
            result.append(name)
    return result


def clean_label(label):
    return LABEL_SUFFIX.sub("", str(label))
