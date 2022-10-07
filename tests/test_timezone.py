import datetime
from babel.dates import get_timezone as babel_get_timezone
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from starlette_babel import timezone
from starlette_babel.timezone import (
    TimezoneFromCookie,
    TimezoneFromQuery,
    TimezoneFromUser,
    TimezoneMiddleware,
    get_timezone,
    set_timezone,
    switch_timezone,
    to_user_timezone,
    to_utc,
)


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive, send)
    await JSONResponse(str(request.state.timezone))(scope, receive, send)


def test_set_get_timezone() -> None:
    set_timezone("Europe/Warsaw")
    set_timezone("Europe/Minsk")
    assert str(get_timezone()) == "Europe/Minsk"

    tz = babel_get_timezone("Europe/Minsk")
    set_timezone(tz)
    assert get_timezone() == tz


def test_switch_timezone() -> None:
    set_timezone("Europe/Warsaw")
    with switch_timezone("Europe/Minsk"):
        assert str(get_timezone()) == "Europe/Minsk"
    assert str(get_timezone()) == "Europe/Warsaw"


def test_to_user_timezone() -> None:
    """
    Europe/Minsk is +3:00.

    Naive dates considered to be in UTC.
    """
    with switch_timezone("Europe/Minsk"):
        naive_dt = datetime.datetime(2022, 12, 25, 12, 30, 59)
        assert to_user_timezone(naive_dt).isoformat() == "2022-12-25T15:30:59+03:00"

        aware_dt = datetime.datetime(2022, 12, 25, 12, 30, 59, tzinfo=babel_get_timezone("CET"))
        assert to_user_timezone(aware_dt).isoformat() == "2022-12-25T14:30:59+03:00"


def test_to_utc() -> None:
    """Naive time will be assigned current timezone (Europe/Minsk) and then converted to UTC."""
    with switch_timezone("Europe/Minsk"):
        naive_dt = datetime.datetime(2022, 12, 25, 12, 30, 59)
        assert to_utc(naive_dt).isoformat() == "2022-12-25T09:30:59"

        aware_dt = datetime.datetime(2022, 12, 25, 12, 30, 59, tzinfo=babel_get_timezone("CET"))
        assert to_utc(aware_dt).isoformat() == "2022-12-25T11:30:59"


def test_now() -> None:
    """It should return datetime respecting current timezone."""
    now = timezone.now()
    assert now.tzname() == "CEST"


def test_now_with_custom_timezone() -> None:
    with switch_timezone("Europe/Minsk"):
        now = timezone.now()
        assert now.tzname() == "+03"


class _User:
    def __init__(self, timezone: str | None) -> None:
        self.timezone = timezone

    def get_timezone(self) -> str | None:
        return self.timezone


class ForceAuthentication:
    def __init__(self, app: ASGIApp, timezone: str | None) -> None:
        self.app = app
        self.timezone = timezone

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["user"] = _User(timezone=self.timezone)
        await self.app(scope, receive, send)


def test_timezone_middleware_detects_tz_from_user() -> None:
    client = TestClient(
        ForceAuthentication(
            TimezoneMiddleware(
                app,
                selectors=[
                    TimezoneFromUser(),
                ],
            ),
            timezone="Europe/Minsk",
        )
    )
    assert client.get("/").json() == "Europe/Minsk"


def test_timezone_middleware_user_supplies_no_timezone() -> None:
    client = TestClient(ForceAuthentication(TimezoneMiddleware(app), timezone=None))
    assert client.get("/").json() == "UTC"


def test_timezone_middleware_detects_tz_from_cookie() -> None:
    client = TestClient(TimezoneMiddleware(app, selectors=[TimezoneFromCookie(cookie_name="tz")]))
    assert client.get("/", cookies={"tz": "Europe/Minsk"}).json() == "Europe/Minsk"


def test_timezone_middleware_detects_tz_from_query() -> None:
    client = TestClient(TimezoneMiddleware(app, selectors=[TimezoneFromQuery(query_param="tz")]))
    assert client.get("/?tz=Europe/Minsk").json() == "Europe/Minsk"


def test_timezone_middleware_detects_invalid_timezone() -> None:
    client = TestClient(
        TimezoneMiddleware(app, fallback="Europe/Warsaw", selectors=[TimezoneFromQuery(query_param="tz")])
    )
    assert client.get("/?tz=invalid").json() == "Europe/Warsaw"


def test_timezone_middleware_fallback_language() -> None:
    client = TestClient(TimezoneMiddleware(app, fallback="Europe/Warsaw"))
    assert client.get("/").json() == "Europe/Warsaw"


def test_timezone_middleware_use_custom_detector() -> None:
    def detector(conn: HTTPConnection) -> str | None:
        return "Europe/Kiev"

    client = TestClient(TimezoneMiddleware(app, selectors=[detector]))
    assert client.get("/").json() == "Europe/Kiev"


def test_timezone_middleware_custom_detector_returns_no_locale() -> None:
    def detector(conn: HTTPConnection) -> str | None:
        return None

    client = TestClient(TimezoneMiddleware(app, selectors=[detector]))
    assert client.get("/").json() == "UTC"
