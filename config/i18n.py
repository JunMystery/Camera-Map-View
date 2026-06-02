"""Runtime UI/UX translation loading from XML string resources."""

from pathlib import Path
from typing import Any
from xml.etree import ElementTree

DEFAULT_LANGUAGE = "vi"
SUPPORTED_LANGUAGES = ("vi", "en", "jp")
STRING_RESOURCE_PURPOSE = "UIUX"
STRING_RESOURCE_FILES = {
    "vi": "UIUX_VI_Strings.xml",
    "en": "UIUX_EN_Strings.xml",
    "jp": "UIUX_JP_Strings.xml",
}

_current_language = DEFAULT_LANGUAGE


def _strings_dir() -> Path:
    """Return the directory containing XML string resources."""
    return Path(__file__).resolve().parent / "strings"


def _load_xml_strings(base_dir: Path | None = None) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Load UI/UX string resources from per-language XML files."""
    base_path = base_dir or _strings_dir()
    translations: dict[str, dict[str, str]] = {}
    language_labels: dict[str, str] = {}
    key_sets: dict[str, set[str]] = {}

    for language in SUPPORTED_LANGUAGES:
        file_path = base_path / STRING_RESOURCE_FILES[language]
        if not file_path.exists():
            raise FileNotFoundError(f"Missing string resource file: {file_path}")
        try:
            root = ElementTree.parse(file_path).getroot()
        except ElementTree.ParseError as exc:
            raise ValueError(f"Invalid XML string resource file: {file_path}") from exc
        _validate_resource_root(root, language, file_path)
        language_labels[language] = root.attrib["label"]
        seen_keys: set[str] = set()
        for element in root.findall("string"):
            key = element.attrib.get("key", "").strip()
            if not key:
                raise ValueError(f"String resource without key in {file_path}")
            if key in seen_keys:
                raise ValueError(f"Duplicate string key '{key}' in {file_path}")
            seen_keys.add(key)
            translations.setdefault(key, {})[language] = element.text or ""
        key_sets[language] = seen_keys

    _validate_language_key_sets(key_sets)
    return translations, language_labels


def _validate_resource_root(root: ElementTree.Element, language: str, file_path: Path) -> None:
    """Validate one XML root element before reading strings."""
    if root.tag != "resources":
        raise ValueError(f"Invalid root tag in {file_path}: {root.tag}")
    if root.attrib.get("purpose") != STRING_RESOURCE_PURPOSE:
        raise ValueError(f"Invalid string resource purpose in {file_path}")
    if root.attrib.get("language") != language:
        raise ValueError(f"Invalid string resource language in {file_path}")
    if not root.attrib.get("label"):
        raise ValueError(f"Missing language label in {file_path}")


def _validate_language_key_sets(key_sets: dict[str, set[str]]) -> None:
    """Ensure every language file contains the same translation keys."""
    expected = key_sets[DEFAULT_LANGUAGE]
    for language, keys in key_sets.items():
        missing = sorted(expected - keys)
        extra = sorted(keys - expected)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"extra={extra}")
            raise ValueError(f"String keys mismatch for {language}: {', '.join(details)}")


TRANSLATIONS, LANGUAGE_LABELS = _load_xml_strings()


def set_language(language: str) -> None:
    """Set the active application language."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    global _current_language
    _current_language = language


def get_language() -> str:
    """Return the active application language."""
    return _current_language


def t(key: str, **placeholders: Any) -> str:
    """Translate a key and apply placeholder values."""
    translations = TRANSLATIONS.get(key)
    if translations is None:
        raise KeyError(f"Missing translation key: {key}")
    template = translations.get(_current_language) or translations[DEFAULT_LANGUAGE]
    return template.format(**placeholders)
