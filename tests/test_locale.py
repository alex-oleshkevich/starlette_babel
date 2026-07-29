import pytest
from babel import Locale
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from starlette_babel.locale import (
    LocaleFromCookie,
    LocaleFromQuery,
    LocaleMiddleware,
    get_language,
    get_locale,
    negotiate_locale,
    parse_accept_language,
    set_locale,
    switch_locale,
)


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive, send)
    await JSONResponse([request.state.locale.language, request.state.locale.territory])(scope, receive, send)


def test_locale_middleware_detects_locale_from_query() -> None:
    """It should read and set locale from the query params."""
    client = TestClient(LocaleMiddleware(app, locales=["be_BY"]))
    assert client.get("/?lang=be_BY").json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_query_using_custom_query_param() -> None:
    """It shojuld read and set locale from the query params using custom query param name."""
    client = TestClient(LocaleMiddleware(app, locales=["be_BY"], selectors=[LocaleFromQuery(query_param="locale")]))
    assert client.get("/?locale=be_BY").json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_cookie() -> None:
    """It should read and set locale from the cookie."""
    client = TestClient(LocaleMiddleware(app, locales=["be_BY"]), cookies={"language": "be_BY"})
    assert client.get("/").json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_cookie_using_custom_name() -> None:
    """It should read and set locale from the cookie using custom cookie name."""
    client = TestClient(
        LocaleMiddleware(app, locales=["be_BY"], selectors=[LocaleFromCookie("lang")]), cookies={"lang": "be_BY"}
    )
    assert client.get("/").json() == ["be", "BY"]


class TestParseAcceptLanguage:
    def test_bare_range_carries_implicit_weight(self) -> None:
        """RFC 9110 12.5.4 states parenthetically that "no value is the same as q=1"."""
        assert parse_accept_language("en") == (("en", 1.0),)

    def test_orders_members_by_descending_weight(self) -> None:
        """The result is a language priority list, so position in the header does not decide."""
        assert parse_accept_language("fr;q=0.5, en") == (("en", 1.0), ("fr", 0.5))

    def test_preserves_header_order_within_equal_weights(self) -> None:
        """Members sharing a weight keep the order the client wrote them in."""
        assert parse_accept_language("en;q=0.5,fr;q=0.5,de;q=0.5") == (("en", 0.5), ("fr", 0.5), ("de", 0.5))

    def test_tolerates_optional_whitespace(self) -> None:
        """Optional whitespace around the member and weight delimiters is tolerated."""
        assert parse_accept_language("fr ; q=0.9 , be_BY") == (("be_bddy", 1.0), ("fr", 0.9))

    @pytest.mark.parametrize(
        ("weight_spec", "expected"),
        (
            ("q=0", 0.0),
            ("q=1", 1.0),
            ("q=0.", 0.0),
            ("q=1.", 1.0),
            ("q=1.0", 1.0),
            ("q=0.123", 0.123),
            ("q=0.000", 0.0),
            ("q=1.000", 1.0),
        ),
    )
    def test_accepts_every_weight_the_qvalue_grammar_allows(self, weight_spec: str, expected: float) -> None:
        """
        The full qvalue grammar is honoured, including its odd-looking corners.

        RFC 9110 12.4.2 fixes qvalue as ( "0" [ "." 0*3DIGIT ] ) / ( "1" [ "." 0*3("0") ] ). The
        fractional part is optional and may be empty after the dot, so 'q=0.' and 'q=1.' are as legal
        as 'q=0.123'; only trailing zeroes are permitted after '1'.
        """
        assert parse_accept_language(f"en;{weight_spec}") == (("en", expected),)

    @pytest.mark.parametrize(
        "weight_spec",
        (
            "q=100",
            "q=-1",
            "q=nan",
            "q=1.001",
            "q=0.1234",
            "q=",
            "",
            "q=.9",
            "q=0.8;q=0.7",
            "q=0.5;charset=utf-8",
        ),
    )
    def test_drops_member_whose_weight_breaks_the_qvalue_grammar(self, weight_spec: str) -> None:
        """A member whose weight breaks the grammar is dropped, not repaired."""
        assert parse_accept_language(f"fr;{weight_spec},be;q=0.9") == (("be", 0.9),)

    def test_keeps_a_refused_member(self) -> None:
        """'q=0' parses; it does not vanish."""
        assert parse_accept_language("en;q=0") == (("en", 0.0),)

    def test_drops_member_without_a_language_range(self) -> None:
        """A member carrying only a weight names no language and is dropped."""
        assert parse_accept_language(";q=1, be;q=0.5") == (("be", 0.5),)

    @pytest.mark.parametrize("header", ("", "   ", ",", ",,"))
    def test_returns_nothing_for_a_header_naming_no_language(self, header: str) -> None:
        """RFC 9110 12.5.4 allows the field to be empty, and empty list members carry no preference."""
        assert parse_accept_language(header) == ()

    def test_skips_empty_members_between_ranges(self) -> None:
        """An empty list member is skipped without disturbing the ranges around it."""
        assert parse_accept_language("en, , fr") == (("en", 1.0), ("fr", 1.0))

    def test_keeps_the_wildcard_as_an_ordinary_range(self) -> None:
        """'*' is parsed as a range like any other, weight included."""
        assert parse_accept_language("*;q=0.2") == (("*", 0.2),)

    def test_keeps_duplicate_ranges(self) -> None:
        """A range repeated at two weights is returned twice.

        RFC 9110 12.5.4 does not forbid the repetition, and deciding which weight wins is a matching
        concern; `LocaleFromHeader` collapses duplicates to their highest weight before matching."""
        assert parse_accept_language("en;q=0.1, en;q=0.9") == (("en", 0.9), ("en", 0.1))

    def test_normalises_case(self) -> None:
        """Ranges are returned exactly as written."""
        assert parse_accept_language("en-US;q=0.5") == (("en-us", 0.5),)


@pytest.mark.parametrize(
    "header",
    (
        "en-US,en;q=0.9,ru-BY;q=0.8,ru;q=0.7,be-BY;q=0.6,be;q=0.5,pl;q=0.4,de;q=0.3",
        "en-US,en;q=0.9;q=0.8,ru-BY;q=0.8,ru;q=0.7,be-BY;q=0.6,be;q=0.5,pl;q=0.4,de;q=0.3",
        "be_BY",
    ),
)
def test_locale_middleware_detects_locale_from_header(header: str) -> None:
    """
    The best acceptable member of a realistic priority list wins.

    Each header states a full RFC 9110 12.5.4 language priority list in which be-BY;q=0.6 is the
    highest-weighted member the server actually supports; everything above it is unsupported and
    everything below is redundant. The second variant additionally carries a malformed
    'en;q=0.9;q=0.8' member, which is discarded without disturbing the rest of the list.
    """
    client = TestClient(LocaleMiddleware(app, locales=["be_BY"]))
    assert client.get("/", headers={"accept-language": header}).json() == ["be", "BY"]


def test_locale_from_header_respects_implicit_priority() -> None:
    """
    A member with no q= carries weight 1.0, so position in the header does not decide.

    RFC 9110 12.5.4 states parenthetically that "no value is the same as q=1", which puts be_BY above
    fr;q=0.9 despite appearing second.
    """
    client = TestClient(LocaleMiddleware(app, locales=["be_BY", "fr"]))
    assert client.get("/", headers={"accept-language": "fr;q=0.9,be_BY"}).json() == ["be", "BY"]


def test_locale_middleware_detects_locale_from_header_with_wildcard() -> None:
    """
    A bare '*' accepts anything, so the first supported locale is served.

    RFC 9110 12.5.4 defines no semantics for '*', delegating all matching to RFC 4647. We follow the
    HTTP/1.1 rule RFC 4647 3.3.1 cites as an example: "the range '*' matches only languages not
    matched by any other range within an 'Accept-Language' header" (RFC 2616 14.4). With no other
    range present it claims everything, so falling back to the default locale here would refuse a
    client that stated no objection.
    """
    client = TestClient(LocaleMiddleware(app, locales=["be_BY"]))
    assert client.get("/", headers={"accept-language": "*"}).json() == ["be", "BY"]


def test_locale_middleware_detects_locale_hyphenated() -> None:
    """
    Supported locales may be written with either separator.

    RFC 4647 2.1 spells ranges with hyphens ('be-BY') while Babel identifies locales with underscores
    ('be_BY'). Both are normalised to one vocabulary before matching, so configuring the middleware in
    tag notation works.
    """
    client = TestClient(LocaleMiddleware(app, locales=["be-BY"]))
    assert client.get("/", headers={"accept-language": "be-BY"}).json() == ["be", "BY"]


def test_locale_middleware_prefers_exact_match_over_truncation() -> None:
    """
    Lookup returns the most specific acceptable locale, not the shortest.

    RFC 4647 3.4 truncates only until a match is found, so 'en-US' stops at the exact en_US and never
    reaches en - even though en is listed first and would also match after one truncation.
    """
    client = TestClient(LocaleMiddleware(app, locales=["en", "en_US"]))
    assert client.get("/", headers={"accept-language": "en-US"}).json() == ["en", "US"]


def test_locale_middleware_detects_locale_from_header_with_locale_after_wildcard() -> None:
    """
    '*' cannot claim a locale that another range already names.

    Per RFC 2616 14.4, preserved via the note in RFC 4647 3.3.1, '*' "matches every tag not matched by
    any other range present in the Accept-Language field". So 'es' is carved out and '*' resolves to
    en. Note '*' is reached first on weight alone: it carries an implicit q=1 against es;q=0.1.
    """
    client = TestClient(LocaleMiddleware(app, locales=["en", "es"]))
    assert client.get("/", headers={"accept-language": "*, es;q=0.1"}).json() == ["en", None]


def test_locale_middleware_detects_locale_from_header_with_last_resort() -> None:
    client = TestClient(LocaleMiddleware(app, locales=["es"]))
    assert client.get("/", headers={"accept-language": "*, es;q=0.1"}).json() == ["es", None]


def test_locale_middleware_detects_locale_from_header_with_locale_after_excluded_wildcard() -> None:
    """
    '*;q=0' refuses everything the client did not name explicitly.

    RFC 9110 12.4.2 makes q=0 "not acceptable", so the wildcard vetoes en rather than selecting it,
    leaving only the explicitly named es;q=0.1 acceptable.
    """
    client = TestClient(LocaleMiddleware(app, locales=["en", "es"]))
    assert client.get("/", headers={"accept-language": "*;q=0, es;q=0.1"}).json() == ["es", None]


def test_locale_middleware_wildcard_claims_nothing_when_all_locales_are_named() -> None:
    """
    '*' selects nothing if every supported locale is already named by another range.

    The HTTP wildcard rule (RFC 2616 14.4, cited by RFC 4647 3.3.1) confines '*' to tags not matched
    by any other range present in the field. Here en is named explicitly, so the wildcard has no
    candidates left and the search moves on to the en range itself rather than stopping.
    """
    client = TestClient(LocaleMiddleware(app, locales=["en"], default_locale="fr"))
    assert client.get("/", headers={"accept-language": "*, en;q=0.5"}).json() == ["en", None]


def test_locale_middleware_detects_locale_ignores_excluded() -> None:
    """
    A q=0 range refuses only the locales it covers, and nothing broader.

    Exclusion is evaluated with RFC 4647 3.3.1 basic filtering rather than lookup truncation: 'en-GB'
    covers en_GB but not en, so 'en;q=1, en-GB;q=0' refuses en_GB while leaving en selectable. Were
    the veto truncated the way selection is, en-GB;q=0 would collapse to en and refuse all English.
    """
    header = {"accept-language": "en;q=1, en-gb;q=0"}

    refused = TestClient(LocaleMiddleware(app, locales=["en_GB", "fr"], default_locale="fr"))
    assert refused.get("/", headers=header).json() == ["fr", None]

    allowed = TestClient(LocaleMiddleware(app, locales=["en", "fr"], default_locale="fr"))
    assert allowed.get("/", headers=header).json() == ["en", None]


def test_locale_middleware_combines_repeated_header_lines() -> None:
    """
    Repeated accept-language field lines form a single comma-joined value.

    RFC 9110 5.2: "When a field name is repeated within a section, its combined field value consists
    of the list of corresponding field line values within that section, concatenated in order, with
    each field line value separated by a comma." The two lines below therefore mean "fr;q=0.5, be",
    so be wins on its implicit q=1 - reading only the first line would have served fr.
    """
    client = TestClient(LocaleMiddleware(app, locales=["be_BY", "fr"]))
    headers = [("accept-language", "fr;q=0.5"), ("accept-language", "be")]
    assert client.get("/", headers=headers).json() == ["be", "BY"]


def test_locale_middleware_supports_language_shortcuts() -> None:
    """It should properly detect locale when user defines list of supported locales without region."""
    client = TestClient(LocaleMiddleware(app, locales=["be"]))
    assert client.get("/?lang=be_BY").json() == ["be", None]


def test_locale_middleware_truncates_range_to_supported_language() -> None:
    """
    A range more specific than anything supported is truncated from the right.

    RFC 4647 3.4 lookup drops the region subtag of 'de-DE' and matches de. Basic filtering (3.3.1)
    would find nothing here, because a range only matches tags at least as specific as itself - this
    test pins the direction that distinguishes the two schemes.
    """
    client = TestClient(LocaleMiddleware(app, locales=["fr", "de"], default_locale="fr"))
    assert client.get("/", headers={"accept-language": "de-DE"}).json() == ["de", None]


def test_locale_middleware_prefers_truncated_range_over_lower_priority_range() -> None:
    """
    Each range is resolved fully before the next one is consulted.

    RFC 4647 3.4 returns "the first matching tag found, according to the user's priority", so 'ca-ES'
    truncating to the supported ca ends the search and es;q=0.9 is never reached. Under basic
    filtering ca-ES would match nothing and a Catalan speaker would be served Spanish.
    """
    client = TestClient(LocaleMiddleware(app, locales=["ca", "es", "en"], default_locale="en"))
    assert client.get("/", headers={"accept-language": "ca-ES,es;q=0.9,en;q=0.8"}).json() == ["ca", None]


def test_locale_middleware_widens_range_to_supported_variant() -> None:
    """
    A range broader than anything supported still resolves, by widening.

    Lookup only ever shortens a range, so 'be' against a supported be_BY would match nothing. This
    library extends 3.4 with a basic-filtering (3.3.1) fallback, which RFC 9110 12.5.4 permits by
    leaving the scheme to the implementation; the alternative is serving the default to a client
    whose language is available.
    """
    client = TestClient(LocaleMiddleware(app, locales=["fr", "be_BY"], default_locale="fr"))
    assert client.get("/", headers={"accept-language": "be"}).json() == ["be", "BY"]


def test_locale_middleware_does_not_truncate_past_an_exclusion() -> None:
    """
    Truncation may not land on a locale the client refused.

    'ca-ES' truncates toward ca, but ca;q=0 vetoes it under RFC 9110 12.4.2, so lookup keeps
    truncating instead of serving a refused locale and ends at the default.
    """
    client = TestClient(LocaleMiddleware(app, locales=["ca", "fr"], default_locale="fr"))
    assert client.get("/", headers={"accept-language": "ca-ES,ca;q=0"}).json() == ["fr", None]


def test_locale_middleware_truncation_drops_singleton_subtags() -> None:
    """
    Single-character subtags are removed together with their trailing subtag.

    RFC 4647 3.4 requires that singletons - the private-use 'x' and extension introducers - never be
    left dangling at the end of a range, so 'zh-x-pig' truncates straight to zh rather than to the
    meaningless 'zh-x'.
    """
    client = TestClient(LocaleMiddleware(app, locales=["zh", "fr"], default_locale="fr"))
    assert client.get("/", headers={"accept-language": "zh-x-pig"}).json() == ["zh", None]


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
    client = TestClient(ForceAuthentication(LocaleMiddleware(app, locales=["be_BY"]), language="be_BY"))
    assert client.get("/").json() == ["be", "BY"]


def test_locale_middleware_user_supplies_no_language() -> None:
    """It should use default locale if user instance cannot provide a locale."""
    client = TestClient(ForceAuthentication(LocaleMiddleware(app, locales=["be_BY"]), language=None))
    assert client.get("/").json() == ["en", "US"]


def test_locale_middleware_finds_variant() -> None:
    """If there is no locale exactly matching the requested, try to find alternate variant that may satisfy the
    client."""

    client = TestClient(LocaleMiddleware(app, locales=["ru_BY"]))
    assert client.get("/?lang=ru_RU").json() == ["ru", "BY"]


def test_locale_middleware_finds_variant_no_dash() -> None:
    """If there is no locale exactly matching the requested, try to find alternate variant that may satisfy the
    client."""

    client = TestClient(LocaleMiddleware(app, locales=["ru"]))
    assert client.get("/?lang=ru_RU").json() == ["ru", None]

    client = TestClient(LocaleMiddleware(app))
    assert client.get("/?lang=ru_RU").json() == ["en", "US"]


def test_locale_middleware_fallback_language() -> None:
    """If there is no locale exactly matching the requested, try to find alternate variant that may satisfy the
    client."""

    client = TestClient(LocaleMiddleware(app, locales=["be_BY"], default_locale="pl_PL"))
    assert client.get("/?lang=ru_RU").json() == ["pl", "PL"]


def test_locale_middleware_use_custom_detector() -> None:
    """It should read and set locale using user-defined selector."""

    def detector(_: HTTPConnection) -> str | None:
        return "be_BY"

    client = TestClient(LocaleMiddleware(app, locales=["be_BY"], selectors=[detector]))
    assert client.get("/").json() == ["be", "BY"]


def test_locale_middleware_custom_detector_returns_no_locale() -> None:
    """
    A case when there is only one detector by it fails to detect a locale.

    The fallback locale to be used.
    """

    def detector(_: HTTPConnection) -> str | None:
        return None

    client = TestClient(LocaleMiddleware(app, locales=["be_BY"], selectors=[detector]))
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


def test_switch_locale_restores_on_exception() -> None:
    set_locale("en_US")
    with pytest.raises(RuntimeError):
        with switch_locale("be_BY"):
            raise RuntimeError("boom")
    assert str(get_locale()) == "en_US"


def test_switch_locale_accepts_locale_object() -> None:
    locale = Locale.parse("be_BY")
    with switch_locale(locale):
        assert str(get_locale()) == "be_BY"


def test_negotiate_locale_exact_match() -> None:
    assert negotiate_locale(["be_BY"], ["be_BY", "en_US"]) == "be_BY"


def test_negotiate_locale_language_only_fallback() -> None:
    # Babel negotiate does language-only fallback: en_US → en if 'en' is available
    assert negotiate_locale(["en_US"], ["en", "fr"]) == "en"


def test_negotiate_locale_no_territory_substitution() -> None:
    # negotiate_locale does NOT substitute territories (en_US → en_GB is not supported)
    assert negotiate_locale(["en_US"], ["en_GB"]) is None


def test_negotiate_locale_no_match() -> None:
    assert negotiate_locale(["zh_CN"], ["en_US", "fr_FR"]) is None


async def test_locale_middleware_invalid_request_type() -> None:
    async def fake_receive() -> Message:
        return {}

    async def fake_send(message: Message) -> None:
        pass

    async def fake_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    scope = {"type": "lifecycle"}
    middleware = LocaleMiddleware(fake_app)
    await middleware({"type": "lifecycle"}, fake_receive, fake_send)
    assert "state" not in scope
