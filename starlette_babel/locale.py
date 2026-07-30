import contextvars as cv
import re
import typing
from contextlib import contextmanager

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


def get_text_direction(locale: Locale | str | None = None) -> typing.Literal["ltr", "rtl"]:
    """
    Get the writing direction of the locale. Uses the current locale when none given.

    Use it to set the `dir` attribute of the HTML document:

    ```html
    <html dir="{{ text_direction() }}">
    ```
    """
    if locale is None:
        locale = get_locale()
    elif isinstance(locale, str):
        locale = Locale.parse(locale)
    return typing.cast(typing.Literal["ltr", "rtl"], locale.text_direction)


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


# RFC 9110 12.4.2: qvalue = ( "0" [ "." 0*3DIGIT ] ) / ( "1" [ "." 0*3("0") ] ).
_QVALUE_RE = re.compile(r"q=(0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)")

MAX_HEADER_LENGTH = 500


def parse_accept_language(header: str) -> tuple[tuple[str, float], ...]:
    """
    Parse an Accept-Language field value into (language range, weight) pairs, best first.

    RFC 9110 12.5.4 defines `Accept-Language = #( language-range [ weight ] )`. A member whose weight
    does not match the qvalue grammar is dropped rather than guessed at, since a malformed member
    carries no reliable preference.
    """
    if len(header) > MAX_HEADER_LENGTH:
        boundary = header.rfind(",", 0, MAX_HEADER_LENGTH)
        header = header[:boundary] if boundary > 0 else ""

    result: list[tuple[str, float]] = []
    for spec in header.split(","):
        spec = spec.strip()
        if not spec:
            continue

        weight = 1.0  # RFC 9110 12.5.4: "no value is the same as q=1".
        lang_range, separator, weight_spec = spec.partition(";")
        lang_range = lang_range.strip()
        if not lang_range:
            continue

        if separator:
            match = _QVALUE_RE.fullmatch(weight_spec.strip())
            if match is None:
                continue
            weight = float(match.group(1))

        result.append((lang_range, weight))
    return tuple(sorted(result, key=lambda x: x[1], reverse=True))


class LocaleFromHeader:
    def __init__(self, supported_locales: typing.Iterable[str]) -> None:
        self.supported_locales = [x.replace("-", "_") for x in supported_locales]

    def __call__(self, conn: HTTPConnection) -> str | None:
        header = ", ".join(conn.headers.getlist("accept-language"))
        ranges = [(r.replace("-", "_"), w) for r, w in parse_accept_language(header) if r != "*"]
        refused = [lang_range.lower() for lang_range, weight in ranges if weight <= 0]

        for lang_range, weight in ranges:
            if weight <= 0:
                continue

            if lang := self._find_exact(lang_range, refused):
                return lang

            if lang := self._find_truncated(lang_range, refused):
                return lang

            if lang := self._find_widened(lang_range, refused):
                return lang

        return None

    def _acceptable(self, locale: str, refused: list[str]) -> bool:
        key = locale.lower()
        return not any(key == lang_range or key.startswith(f"{lang_range}_") for lang_range in refused)

    def _find_exact(self, lang_range: str, refused: list[str]) -> str | None:
        for supported in self.supported_locales:
            if supported.lower() == lang_range.lower() and self._acceptable(supported, refused):
                return supported
        return None

    def _find_truncated(self, lang_range: str, refused: list[str]) -> str | None:
        for truncated in self._truncate(lang_range):
            for supported in self.supported_locales:
                if supported.lower() == truncated.lower() and self._acceptable(supported, refused):
                    return supported
        return None

    def _find_widened(self, lang_range: str, refused: list[str]) -> str | None:
        for truncated in self._truncate(lang_range):
            for supported in self.supported_locales:
                if supported.lower().startswith(f"{truncated.lower()}_") and self._acceptable(supported, refused):
                    return supported
        return None

    def _truncate(self, lang_range: str) -> typing.Generator[str, None, None]:
        head = lang_range
        while head:
            yield head
            head, separator, _ = head.rpartition("_")
            if not separator:
                return
            while head and len(head.rsplit("_", 1)[-1]) == 1:
                head = head.rpartition("_")[0]


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
        scope["state"].update(
            {"locale": locale, "language": locale.language, "text_direction": get_text_direction(locale)}
        )
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
