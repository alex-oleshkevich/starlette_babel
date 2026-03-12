import contextvars as cv
import typing
from contextlib import contextmanager
from functools import lru_cache

from babel import Locale
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_current_locale: cv.ContextVar[Locale] = cv.ContextVar("current_locale", default=Locale.parse("en_US"))


def get_locale() -> Locale:
    """Return currently active locale."""
    return _current_locale.get()


def set_locale(locale: Locale | str) -> None:
    """Set active locale."""
    if isinstance(locale, str):
        locale = Locale.parse(locale)
    _current_locale.set(locale)


@contextmanager
def switch_locale(locale: Locale | str) -> typing.Generator[None, None, None]:
    """
    Temporary switch current locale for a code block. The previous locale will be restored after exiting the manager.
    Use is any other context manager:

    ```python
    from starlette_babel import switch_locale, gettext_lazy

    message = gettext_lazy('Welcome')

    with switch_locale('be_BY'):
        assert message == 'Вітаем'

    with switch_locale('pl'):
        assert message == 'Witamy'
    ```
    """
    old_locale = get_locale()
    set_locale(locale)
    try:
        yield
    finally:
        set_locale(old_locale)


def get_language() -> str:
    """Get current language."""
    return get_locale().language


LocaleSelector = typing.Callable[[HTTPConnection], str | None]


class LocaleFromQuery:
    """
    Select locale from query params.

    Will look up `query_param` and return its value once found.
    """

    def __init__(self, query_param: str = "lang") -> None:
        self.query_param = query_param

    def __call__(self, conn: HTTPConnection) -> str | None:
        return conn.query_params.get(self.query_param)


class LocaleFromCookie:
    """
    Select locale from cookies.

    Will look up `cookie_name` and return its value once found.
    """

    def __init__(self, cookie_name: str = "language") -> None:
        self.cookie_name = cookie_name

    def __call__(self, conn: HTTPConnection) -> str | None:
        return conn.cookies.get(self.cookie_name)


class LocaleFromHeader:
    """
    Select locale from Accept-Language header.

    Will iterate over header value trying to find a supported locale.
    """

    def __init__(self, supported_locales: typing.Iterable[str]) -> None:
        self.supported_locales = list(map(str.lower, supported_locales))

    def __call__(self, conn: HTTPConnection) -> str | None:
        header = conn.headers.get("accept-language", "").lower()
        for lang, _ in self._get_languages_from_header(header):
            lang = lang.lower().replace("-", "_")
            if lang == "*":
                break

            if lang in self.supported_locales:
                return lang
        return None

    @staticmethod
    @lru_cache(maxsize=1000)
    def _get_languages_from_header(header: str) -> list[tuple[str, float]]:
        parts = header.split(",")
        result = []
        for part in parts:
            part = part.strip()
            if ";" in part:
                locale, _, qpart = part.partition(";")
                locale = locale.strip()
                try:
                    priority = float(qpart.strip()[2:])
                except (ValueError, IndexError):
                    priority = 1.0
            else:
                locale = part
                priority = 1.0
            result.append((locale, priority))
        return sorted(result, key=lambda x: x[1], reverse=True)


class LocaleFromUser:
    def __init__(self, getter_method: str = "get_preferred_language") -> None:
        self.getter_method = getter_method

    def __call__(self, conn: HTTPConnection) -> str | None:
        if "user" in conn.scope and hasattr(conn.user, self.getter_method):
            getter: typing.Callable[[], str] = getattr(conn.user, self.getter_method)
            return getter()
        return None


def negotiate_locale(preferred: list[str], available: list[str]) -> str | None:
    """
    Negotiate the best matching locale from a list of preferred locales against a list of available locales.

    Uses Babel's locale negotiation which handles script subtags and aliases.
    Tries exact match first, then language-only match (e.g. 'en_US' → 'en' if 'en' is available).
    Returns the best matching locale identifier string, or None if no match is found.

    Example:
        ```python
        from starlette_babel import negotiate_locale

        negotiate_locale(['be_BY', 'en'], ['en_US', 'fr'])  # 'en_US' via language match
        negotiate_locale(['zh_CN'], ['en_US', 'fr'])        # None — no match
        ```
    """
    result = Locale.negotiate(preferred, available)
    return str(result) if result is not None else None


class LocaleMiddleware:
    """
    Detect current locale from the request. The middleware asks selectors to provide the current locale. If none
    selectors can detect the `default_locale` will be set.

    You can retrieve current locale by using `starlette_babel.get_locale` utility.
    """

    def __init__(
        self,
        app: ASGIApp,
        locales: list[str] | None = None,
        default_locale: str = "en_US",
        selectors: list[LocaleSelector] | None = None,
    ) -> None:
        self.app = app
        self.locales = [x.replace("-", "_") for x in (locales or ["en_US"])]
        self.default_locale = default_locale
        self.selectors = selectors or [
            LocaleFromQuery(),
            LocaleFromCookie(),
            LocaleFromUser(),
            LocaleFromHeader(supported_locales=locales or [default_locale]),
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("content-language", scope["state"]["language"])
            await send(message)

        locale = self.detect_locale(HTTPConnection(scope))
        set_locale(locale)
        scope.setdefault("state", {})
        scope["state"].update({"locale": locale, "language": locale.language})
        await self.app(scope, receive, send_wrapper)

    def detect_locale(self, conn: HTTPConnection) -> Locale:
        detected = self.default_locale
        for selector in self.selectors:
            if locale := selector(conn):
                detected = locale
                break

        variant = self._find_variant(detected.replace("-", "_")) or self.default_locale
        return Locale.parse(variant)

    def _find_variant(self, locale: str) -> str | None:
        """
        Look up requested locale in supported list.

        Tries exact match first, then language-only match to find any supported variant for the same language.
        For example, if the client requests en_US but only en_GB is supported, returns en_GB.
        """
        locale = locale.lower()
        lang = locale.split("_")[0]
        for supported in self.locales:
            if supported.lower() == locale:
                return supported
        for supported in self.locales:
            supported_lang = supported.lower().split("_")[0]
            if supported_lang == lang:
                return supported
        return None
