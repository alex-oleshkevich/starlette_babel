import pathlib
import pytest
from babel.support import Translations

from starlette_babel import switch_locale
from starlette_babel.translator import LazyString, Translator, get_translator

LOCALE_DIR = pathlib.Path(__file__).parent / "locales"
EXTRA_LOCALE_DIR = pathlib.Path(__file__).parent / "extra_locales"
BROKEN_LOCALE_DIR = pathlib.Path(__file__).parent / "broken_locales"


def test_load_from_directory_should_raise_for_files() -> None:
    with pytest.raises(ValueError, match="Not a locale directory"):
        Translator(directories=[BROKEN_LOCALE_DIR / "locale_is_file"])


def test_load_from_directory_should_not_raise_for_pot_files() -> None:
    Translator(directories=[BROKEN_LOCALE_DIR / "has_pot"])
    assert True


def test_load_from_directory_should_raise_is_lc_messages_missing() -> None:
    with pytest.raises(FileNotFoundError):
        Translator(directories=[BROKEN_LOCALE_DIR / "no_lc_messages"])


def test_loads_from_directories_on_init() -> None:
    """It should load messages from one or multiple paths passed via constructor."""
    translator = Translator(directories=[LOCALE_DIR, EXTRA_LOCALE_DIR])
    assert translator.gettext("Hello", locale="be") == "Вітаем"
    assert translator.gettext("Extra", locale="be") == "BE: Extra"
    assert translator.gettext("Extra", locale="be", domain="errors") == "BE: ERR: Extra"


def test_loads_from_directories() -> None:
    """It should load messages from one or multiple paths via load_from_directories."""
    translator = Translator()
    translator.load_from_directories([LOCALE_DIR, EXTRA_LOCALE_DIR])
    assert translator.gettext("Hello", locale="be") == "Вітаем"
    assert translator.gettext("Extra", locale="be") == "BE: Extra"
    assert translator.gettext("Extra", locale="be", domain="errors") == "BE: ERR: Extra"


def test_loads_from_directory() -> None:
    """It should load messages from the directory."""
    translator = Translator()
    translator.load_from_directory(EXTRA_LOCALE_DIR)
    assert translator.gettext("Hello", locale="be") == "Hello"
    assert translator.gettext("Extra", locale="be") == "BE: Extra"
    assert translator.gettext("Extra", locale="be", domain="errors") == "BE: ERR: Extra"


def test_adds_translations() -> None:
    """It should dynamically add prepared translations."""
    translator = Translator()
    assert translator.gettext("Hello", locale="be") == "Hello"

    translations = Translations.load(LOCALE_DIR, domain="messages", locales="be")
    translator.add_translations("be", translations)
    assert translator.gettext("Hello", locale="be") == "Вітаем"


def test_merges_translations() -> None:
    """It should dynamically add prepared translations."""
    translator = Translator()
    assert translator.gettext("Hello", locale="be") == "Hello"

    translations = Translations.load(LOCALE_DIR, domain="messages", locales="be")
    extra_translations = Translations.load(EXTRA_LOCALE_DIR, domain="messages", locales="be")
    translator.add_translations("be", translations)
    translator.add_translations("be", extra_translations)

    assert translator.gettext("Hello", locale="be") == "Вітаем"
    assert translator.gettext("Extra", locale="be") == "BE: Extra"


def test_translates_singular_for_default_domain() -> None:
    """It should translate singular message form for the default domain."""
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.gettext("Hello", locale="be") == "Вітаем"


def test_translates_singular_for_selected_domain() -> None:
    """It should translate singular message form for selected domain."""
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.gettext("Error", locale="be", domain="errors") == "Памылка"


def test_translates_common_singular_for_selected_domain() -> None:
    """
    Both messages and errors domain have same msgid.

    Each domain has own translation for it.
    """
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.gettext("Shared", locale="be") == "Агульны"
    assert translator.gettext("Shared", locale="be", domain="errors") == "ERR: Агульны"


def test_translates_plural_for_default_domain() -> None:
    """It should translate plural form of the message for the default domain."""
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.ngettext("{count} apple", "{count} apples", 1, locale="be") == "1 яблык"
    assert translator.ngettext("{count} apple", "{count} apples", 2, locale="be") == "2 яблыкі"
    assert translator.ngettext("{count} apple", "{count} apples", 5, locale="be") == "5 яблыкаў"


def test_translates_plural_for_selected_domain() -> None:
    """It should translate plural form of the message for the default domain."""
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.ngettext("{count} error", "{count} errors", 1, locale="be", domain="errors") == "1 памылка"
    assert translator.ngettext("{count} error", "{count} errors", 2, locale="be", domain="errors") == "2 памылкi"
    assert translator.ngettext("{count} error", "{count} errors", 5, locale="be", domain="errors") == "5 памылак"


def test_translates_command_plural_for_selected_domain() -> None:
    """It should translate plural form of the message for the default domain."""
    translator = Translator(directories=[LOCALE_DIR])
    assert translator.ngettext("{count} apple", "{count} apples", 1, locale="be") == "1 яблык"
    assert translator.ngettext("{count} apple", "{count} apples", 2, locale="be") == "2 яблыкі"
    assert translator.ngettext("{count} apple", "{count} apples", 5, locale="be") == "5 яблыкаў"

    assert translator.ngettext("{count} apple", "{count} apples", 1, locale="be", domain="errors") == "ERR: 1 яблык"
    assert translator.ngettext("{count} apple", "{count} apples", 2, locale="be", domain="errors") == "ERR: 2 яблыкі"
    assert translator.ngettext("{count} apple", "{count} apples", 5, locale="be", domain="errors") == "ERR: 5 яблыкаў"


def test_lazy_string_for_singular() -> None:
    translator = Translator(directories=[LOCALE_DIR])
    string = LazyString("Hello", translator=translator)
    with switch_locale("be"):
        assert string == "Вітаем"
    with switch_locale("pl"):
        assert string == "Witamy"


def test_lazy_string_for_plural() -> None:
    translator = Translator(directories=[LOCALE_DIR])
    string = LazyString("{count} apple", "{count} apples", count=1, translator=translator)
    with switch_locale("be"):
        assert string == "1 яблык"
    with switch_locale("pl"):
        assert string == "1 jabłko"


def test_uses_shared_translator() -> None:
    translator = get_translator()
    translator.load_from_directory(LOCALE_DIR)
    string = LazyString("Hello")
    with switch_locale("be"):
        assert string == "Вітаем"
    with switch_locale("pl"):
        assert string == "Witamy"


def test_translates_domain() -> None:
    translator = Translator(directories=[LOCALE_DIR])
    string = LazyString("Error", translator=translator)
    error_string = LazyString("Error", translator=translator, domain="errors")
    with switch_locale("be"):
        assert string == "Error"
        assert error_string == "Памылка"
    with switch_locale("pl"):
        assert string == "Error"
        assert error_string == "Błąd"
