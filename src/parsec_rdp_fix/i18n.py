"""Display translations. The English catalog defines required keys."""

from __future__ import annotations

import ctypes
import json
import locale
import sys
from pathlib import Path

LANGUAGES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
    "ru": "Русский",
    "zh": "简体中文",
    "ja": "日本語",
}


def catalog_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "locales"
    return Path(__file__).resolve().parents[2] / "locales"


def system_language() -> str:
    """Match the Windows user interface language, otherwise use English."""
    language = ""
    if sys.platform == "win32":
        try:
            language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            language = {
                0x16: "pt",
                0x09: "en",
                0x0A: "es",
                0x19: "ru",
                0x04: "zh",
                0x11: "ja",
            }.get(language_id & 0x03FF, "en")
        except (OSError, AttributeError):
            pass

    if not language:
        language = (locale.getlocale()[0] or "").split("_")[0].lower()
        language = {
            "english": "en",
            "portuguese": "pt",
            "spanish": "es",
            "russian": "ru",
            "chinese": "zh",
            "japanese": "ja",
        }.get(language, language)
    return language if language in LANGUAGES else "en"


class Translator:
    def __init__(self, language: str | None = None, directory: Path | None = None):
        self.directory = directory or catalog_dir()
        self.fallback = self._read("en")
        self.language = language if language in LANGUAGES else system_language()
        self.catalog = self._read(self.language)

    def _read(self, language: str) -> dict[str, str]:
        return json.loads((self.directory / f"{language}.json").read_text(encoding="utf-8"))

    def set_language(self, language: str) -> None:
        self.language = language
        self.catalog = self._read(language)

    def __call__(self, key: str) -> str:
        return self.catalog.get(key, self.fallback.get(key, key))
