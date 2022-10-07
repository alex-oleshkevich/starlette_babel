from babel import Locale
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

from starlette_babel.locale import (
    LocaleFromCookie,
    LocaleFromQuery,
    LocaleMiddleware,
    get_language,
    get_locale,
    set_locale,
    switch_locale,
)


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive, send)
    await JSONResponse([request.state.locale.language, request.state.locale.territory])(scope, receive, send)


def test_locale_middleware_detects_locale_from_query() -> None:
    """It should read and set locale from the query params."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"]))
    assert client.get("/?lang=be_BY").json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_query_using_custom_query_param() -> None:
    """It shojuld read and set locale from the query params using custom query param name."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"], selectors=[LocaleFromQuery(query_param="locale")]))
    assert client.get("/?locale=be_BY").json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_cookie() -> None:
    """It should read and set locale from the cookie."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"]))
    assert client.get("/", cookies={"language": "be_BY"}).json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_cookie_using_custom_name() -> None:
    """It should read and set locale from the cookie using custom cookie name."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"], selectors=[LocaleFromCookie("lang")]))
    assert client.get("/", cookies={"lang": "be_BY"}).json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_header() -> None:
    """It should read and set locale from the accept-language header."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"]))
    assert client.get(
        "/", headers={"accept-language": "en-US,en;q=0.9,ru-BY;q=0.8,ru;q=0.7,be-BY;q=0.6,be;q=0.5,pl;q=0.4,de;q=0.3"}
    ).json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_header_with_wildcard() -> None:
    """It should handle a case when accept-language has wildcard '*' value."""
    client = TestClient(LocaleMiddleware(app, languages=["be_BY"]))
    assert client.get("/", headers={"accept-language": "*"}).json() == ["en", "US"]


def test_locale_middleware_supports_language_shortcuts() -> None:
    """It should properly detect locale when user defines list of supported locales without region."""
    client = TestClient(LocaleMiddleware(app, languages=["be"]))
    assert client.get("/?lang=be_BY").json() == ["be", None]


class _User:
    def __init__(self, language: str | None) -> None:
        self.language = language

    def get_preferred_language(self) -> str | None:
        return self.language


class ForceAuthentication:
    def __init__(self, app: ASGIApp, language: str | None) -> None:
        self.app = app
        self.language = language

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["user"] = _User(language=self.language)
        await self.app(scope, receive, send)


def test_locale_middleware_detects_locale_from_user() -> None:
    """It should read and set locale from the user."""
    client = TestClient(ForceAuthentication(LocaleMiddleware(app, languages=["be_BY"]), language="be_BY"))
    assert client.get("/").json() == ["be", "BY"]


def test_locale_middleware_user_supplies_no_language() -> None:
    """It should use default locale if user instance cannot provide a locale."""
    client = TestClient(ForceAuthentication(LocaleMiddleware(app, languages=["be_BY"]), language=None))
    assert client.get("/").json() == ["en", "US"]


def test_locale_middleware_finds_variant() -> None:
    """If there is no locale exactly matching the requested, try to find alternate variant that may satisfy the
    client."""

    client = TestClient(LocaleMiddleware(app, languages=["ru_BY"]))
    assert client.get("/?lang=ru_RU").json() == ["ru", "BY"]


def test_locale_middleware_fallback_language() -> None:
    """If there is no locale exactly matching the requested, try to find alternate variant that may satisfy the
    client."""

    client = TestClient(LocaleMiddleware(app, languages=["be_BY"], default_locale="pl_PL"))
    assert client.get("/?lang=ru_RU").json() == ["pl", "PL"]


def test_locale_middleware_use_custom_detector() -> None:
    """It should read and set locale using user-defined selector."""

    def detector(_: HTTPConnection) -> str | None:
        return "be_BY"

    client = TestClient(LocaleMiddleware(app, languages=["be_BY"], selectors=[detector]))
    assert client.get("/").json() == ["be", "BY"]


def test_locale_middleware_custom_detector_returns_no_locale() -> None:
    """
    A case when there is only one detector by it fails to detect a locale.

    The fallback locale to be used.
    """

    def detector(_: HTTPConnection) -> str | None:
        return None

    client = TestClient(LocaleMiddleware(app, languages=["be_BY"], selectors=[detector]))
    assert client.get("/").json() == ["en", "US"]


def test_set_get_locale() -> None:
    set_locale("en_US")
    set_locale("be_BY")
    assert str(get_locale()) == "be_BY"

    locale = Locale("be_BY")
    set_locale(locale)
    assert get_locale() == locale


def test_temporary_switch_locale() -> None:
    set_locale("en_US")
    with switch_locale("be_BY"):
        assert str(get_locale()) == "be_BY"
    assert str(get_locale()) == "en_US"


def test_get_language() -> None:
    set_locale("be_BY")
    assert get_language() == "be"
