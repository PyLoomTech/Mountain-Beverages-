from . import i18n


def en(model, data):
    """
    Rename translated fields to their English version, the way the dashboard form
    posts them ("name" becomes "name_en"). Models without translation are unchanged.
    """
    translated = i18n.translated_names(model)
    code = i18n.default_language()
    return {(i18n.localized_name(key, code) if key in translated else key): value
            for key, value in data.items()}
