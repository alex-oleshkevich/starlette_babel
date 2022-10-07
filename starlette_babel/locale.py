import contextvars as cv
import typing
from babel import Locale
from contextlib import contextmanager
from functools import lru_cache
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_current_locale: cv.ContextVar[Locale] = cv.ContextVar("current_locale", default=Locale.parse("en_US"))


def get_locale() -> Locale:
    """Return currently active locale."""
    return _current_locale.get()


def set_locale(locale: Locale | str) -> None:
    """Set active locale."""
    if isinstance(locale, str):
        locale = typing.cast(Locale, Locale.parse(locale))
    _current_locale.set(locale)


@contextmanager
def switch_locale(locale: str) -> typing.Generator[None, None, None]:
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
    yield
    set_locale(old_locale)


def get_language() -> str:
    """Get current language."""
    return typing.cast(str, get_locale().language)


LocaleSelector = typing.Callable[[HTTPConnection], str | None]


class LocaleFromQuery:
    """
    Select locale from query params.

    Will look up `query_param` and return its value once found.
    """

    def __init__(self, query_param: str = "lang") -> None:
        self.query_param = query_param

    def __call__(self, conn: HTTPConnection) -> str | None:
        return typing.cast(str, conn.query_params.get(self.query_param, ""))


class LocaleFromCookie:
    """
    Select locale from cookies.

    Will look up `cookie_name` and return its value once found.
    """

    def __init__(self, cookie_name: str = "language") -> None:
        self.cookie_name = cookie_name

    def __call__(self, conn: HTTPConnection) -> str | None:
        return typing.cast(str, conn.cookies.get(self.cookie_name, ""))


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

    @lru_cache(maxsize=1000)
    def _get_languages_from_header(self, header: str) -> list[tuple[str, float]]:
        parts = header.split(",")
        result = []
        for part in parts:
            if ";" in part:
                locale, priority_ = part.split(";")
                priority = float(priority_[2:])
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
        self.locales = {x.lower().replace("-", "_") for x in (locales or ["en"])}
        self.default_locale = default_locale
        self.selectors = selectors or [
            LocaleFromQuery(),
            LocaleFromCookie(),
            LocaleFromUser(),
            LocaleFromHeader(supported_locales=locales or [default_locale]),
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"].append(tuple([b"content-language", scope["state"]["language"].encode()]))
            await send(message)

        locale = self.detect_locale(HTTPConnection(scope))
        set_locale(locale)
        scope.setdefault("state", {})
        scope["state"].update({"locale": locale, "language": locale.language})
        await self.app(scope, receive, send_wrapper)

    def detect_locale(self, conn: HTTPConnection) -> Locale:
        lang = self.default_locale
        for selector in self.selectors:
            if locale := selector(conn):
                lang = locale
                break

        variant = self.find_variant(lang) or self.default_locale
        return typing.cast(Locale, Locale.parse(variant))

    def find_variant(self, locale: str) -> str | None:
        """
        Look up requested locale in supported list.

        If the locale does not exist, it will attempt to find the closest locale from the all supported. For example, if
        clients requests en_US, but we support only "en_GB" then en_GB to be returned. If no locales match request then
        None returned.
        """
        from_locale, _ = locale.lower().split("_") if "_" in locale else [locale, ""]
        for supported in self.locales:
            if "_" in supported:
                language, _ = supported.lower().split("_")
                if language == from_locale:
                    return supported
            elif from_locale.lower() == supported.lower():
                return supported
        return None
