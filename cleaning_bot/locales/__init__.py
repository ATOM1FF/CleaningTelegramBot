import importlib
from typing import Any

SUPPORTED_LANGUAGES = ("uz", "ru", "en")
LANGUAGE_NAMES = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}


def get_locale(language: str) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        language = "uz"
    module = importlib.import_module(f"locales.{language}")
    return module.TEXTS
