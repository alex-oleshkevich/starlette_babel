from __future__ import annotations

import os
import typing
from babel.support import LazyProxy, NullTranslations, Translations

from starlette_babel.locale import get_locale

AnyTranslations = NullTranslations | Translations


class LazyString(LazyProxy):
    """
    Use lazy strings to mark strings as translatable. Such strings will be automatically translated into current
    language at runtime. In other frameworks it is known as `_`, or `gettext_lazy`.

    Example:
        ```python
        from starlette_babel import LazyString

        msg = LazyString('Welcome')
        str(msg) == 'Wilkommen'
        ```

    `gettext_lazy` shortcut also available:
    ```python
    from starlette_babel import gettext_lazy

    msg = gettext_lazy('Welcome')
    ```

    You can use underscore pattern by aliasing this class or function:
    ```python
    from starlette_babel import LazyString as _
    # or
    from starlette_babel import gettext_lazy as _

    msg = _('Welcome')
    ```
    """

    def __init__(
        self,
        msgid: str,
        msgid_plural: str | None = None,
        count: int | None = None,
        domain: str = "messages",
        translator: Translator | None = None,
    ) -> None:
        object.__setattr__(self, "msgid", msgid)
        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "msgid_plural", msgid_plural)
        object.__setattr__(self, "count", count)
        object.__setattr__(self, "translator", translator or get_translator())
        super().__init__(self.translate, enable_cache=False)

    def translate(self) -> str:
        locale = get_locale()
        if self.msgid_plural:
            value = self.translator.ngettext(
                singular=self.msgid,
                plural=self.msgid_plural,
                count=self.count,
                locale=str(locale),
                domain=self.domain,
            )
        else:
            value = self.translator.gettext(msgid=self.msgid, locale=str(locale), domain=self.domain)
        return typing.cast(str, value)


gettext_lazy = LazyString


def gettext(
    msgid: str,
    locale: str | None = None,
    domain: str = "messages",
    translator: Translator | None = None,
) -> str:
    """Translate message."""
    locale = str(locale if locale else get_locale())
    translator = translator or get_translator()
    return translator.gettext(msgid=msgid, locale=str(locale), domain=domain)


def ngettext(
    singular: str,
    plural: str,
    count: int,
    locale: str | None = None,
    domain: str = "messages",
    translator: Translator | None = None,
) -> str:
    """Translate message."""
    locale = str(locale if locale else get_locale())
    translator = translator or get_translator()
    return translator.ngettext(singular=singular, plural=plural, count=count, locale=str(locale), domain=domain)


class Translator:
    """Translator object is a container for translation messages that provides API to translate messages.
    Usage:
    ```python
    from starlette_babel import Translator
    translator = Translator(['path/to/locales_dir'])
    translator.gettext('Welcome')
    ```

    A shared instance (process global) also available by calling `get_translator`:
    ```python
    from starlette_babel import get_get_translator

    translator = get_get_translator()
    translator.load_from_directory('/path/to/locales_dir')
    translator.gettext('Welcome')
    ```
    """

    shared_translator: Translator

    def __init__(self, directories: list[str | os.PathLike[str]] | None = None) -> None:
        self._cache: dict[str, dict[str, Translations]] = {}
        if directories:
            self.load_from_directories(directories)

    def add_translations(self, locale: str, translations: Translations, domain: str = "messages") -> None:
        """
        Add additional translations for this translator.

        If locale or domain already exists, translations will be merged.
        """
        if locale not in self._cache:
            self._cache[locale] = {domain: translations}
            return

        if domain not in self._cache[locale]:
            self._cache[locale][domain] = translations
            return

        self._cache[locale][domain].merge(translations)  # type: ignore[no-untyped-call]

    def load_from_directories(self, directories: list[str | os.PathLike[str]]) -> None:
        """
        Iterate over directories and local messages from them.

        Automatically detects locale and domain using file and directory names.
        """
        for directory in directories:
            self.load_from_directory(directory)

    def load_from_directory(self, directory: str | os.PathLike[str]) -> None:
        """
        Load messages from the directory.

        Automatically detects locale and domain using file and directory names.
        """
        for locale in os.listdir(directory):
            locale_path = os.path.join(directory, locale)
            if os.path.isfile(locale_path):
                if locale_path.endswith(".pot") or os.path.basename(locale_path).startswith("."):
                    continue
                raise ValueError(f"Not a locale directory: {locale_path}. It is a file.")

            for filename in os.listdir(os.path.join(directory, str(locale), "LC_MESSAGES")):
                domain, _ = os.path.splitext(filename)
                translations = Translations.load(str(directory), [locale], domain)
                self.add_translations(str(locale), translations, domain)

    def get_translations(self, locale: str, domain: str = "messages") -> AnyTranslations:
        """
        Get translations for locale and domain.

        If locale or domain is not registered, returns NullTranslations.
        """

        # try exact match (eg. en, en_US)
        if translations := self._cache.get(locale, {}).get(domain):
            return translations

        # fallback: try to find translation using locale name (eg. en)
        lang, *_ = locale.split("_")
        return self._cache.get(lang, {}).get(domain, NullTranslations())

    def gettext(self, msgid: str, locale: str, domain: str = "messages") -> str:
        """Translate msgid."""
        translations = self.get_translations(locale=locale, domain=domain)
        return translations.gettext(msgid)

    def ngettext(self, singular: str, plural: str, count: int, locale: str, domain: str = "messages") -> str:
        """Translate msgid (plural form)."""
        translations = self.get_translations(locale=locale, domain=domain)
        return translations.ngettext(singular, plural, count).format(count=count)


Translator.shared_translator = Translator()


def load_messages_from_directories(directories: list[str | os.PathLike[str]]) -> None:
    """A helper to load messages from directories into shared translator."""
    Translator.shared_translator.load_from_directories(directories)


def get_translator() -> Translator:
    """Get globally configured translator."""
    return Translator.shared_translator
