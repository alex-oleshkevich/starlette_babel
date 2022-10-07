import contextvars as cv
import datetime
import typing
from babel.dates import get_timezone as babel_get_timezone
from babel.util import UTC
from contextlib import contextmanager
from pytz import BaseTzInfo
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

_current_timezone: cv.ContextVar[BaseTzInfo] = cv.ContextVar("current_timezone", default=UTC)


def get_timezone() -> BaseTzInfo:
    """Return currently active timezone."""
    return _current_timezone.get()


def set_timezone(timezone: str | BaseTzInfo) -> None:
    """Set timezone for current request."""
    if isinstance(timezone, str):
        timezone = babel_get_timezone(timezone)
    assert not isinstance(timezone, str)
    _current_timezone.set(timezone)


@contextmanager
def switch_timezone(tz: str | BaseTzInfo) -> typing.Generator[None, None, None]:
    """
    Temporary switch current timezone for a code block. The previous timezone will be restored after exiting the
    manager. Use is any other context manager:

    ```python
    from starlette_babel import set_timezone, timezone

    with set_timezone('Europe/Minsk'):
        ...
    """
    old_timezone = get_timezone()
    set_timezone(tz)
    yield
    set_timezone(old_timezone)


def to_user_timezone(dt: datetime.datetime) -> datetime.datetime:
    """Convert datetime instance into current timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    tzinfo = get_timezone()
    return dt.astimezone(tzinfo)


def to_utc(dt: datetime.datetime) -> datetime.datetime:
    """Convert datetime instance to UTC and drop tzinfo (creates a naive datetime object)."""
    if dt.tzinfo is None:
        dt = get_timezone().localize(dt)
    return dt.astimezone(UTC).replace(tzinfo=None)


def now() -> datetime.datetime:
    """Get current time in user timezone."""
    _now = datetime.datetime.utcnow()
    return to_user_timezone(_now)


TimezoneSelector = typing.Callable[[HTTPConnection], str | None]


class TimezoneFromUser:
    """Asks `request.user` to provide a timezone."""

    def __init__(self, getter_method: str = "get_timezone") -> None:
        self.getter_method = getter_method

    def __call__(self, conn: HTTPConnection) -> str | None:
        if "user" in conn.scope and hasattr(conn.user, self.getter_method):
            callback: typing.Callable[[], str | None] = getattr(conn.user, self.getter_method)
            return callback()
        return None


class TimezoneFromQuery:
    """Try to get timezone from query params."""

    def __init__(self, query_param: str = "tz") -> None:
        self.query_param = query_param

    def __call__(self, conn: HTTPConnection) -> str | None:
        return typing.cast(str, conn.query_params.get(self.query_param, ""))


class TimezoneFromCookie:
    """Try to get timezone from cookie."""

    def __init__(self, cookie_name: str = "timezone") -> None:
        self.cookie_name = cookie_name

    def __call__(self, conn: HTTPConnection) -> str | None:
        return typing.cast(str, conn.cookies.get(self.cookie_name, ""))


class TimezoneMiddleware:
    """
    Detect current timezone from the request. The middleware asks selectors to provide the timezone. If none selectors
    can detect the `fallback` will be set.

    You can retrieve current timezone by using `starlette_babel.get_timezone` utility.

    All selected timezones validated by Babel and if selector returns an invalid timezone then the fallback
    will be used. If fallback is also an invalid timezone then LookupError raised.
    """

    def __init__(
        self,
        app: ASGIApp,
        fallback: str = "UTC",
        selectors: list[TimezoneSelector] | None = None,
    ) -> None:
        self.app = app
        self.fallback = fallback
        self.selectors = selectors or [
            TimezoneFromQuery(),
            TimezoneFromCookie(),
            TimezoneFromUser(),
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        conn = HTTPConnection(scope)
        tz = self.detect_timezone(conn) or self.fallback
        try:
            tz_info = babel_get_timezone(tz)
        except LookupError:
            tz_info = babel_get_timezone(self.fallback)

        with switch_timezone(tz_info):
            conn.state.timezone = tz_info
            await self.app(scope, receive, send)

    def detect_timezone(self, conn: HTTPConnection) -> str | None:
        for selector in self.selectors:
            if tz := selector(conn):
                return tz
        return None
