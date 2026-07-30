import pytest
from babel import Locale
from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from starlette_babel.locale import (
    MAX_HEADER_LENGTH,
    LocaleFromCookie,
    LocaleFromHeader,
    LocaleFromQuery,
    LocaleFromUser,
    LocaleMiddleware,
    get_language,
    get_locale,
    get_text_direction,
    negotiate_locale,
    parse_accept_language,
    set_locale,
    switch_locale,
)


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive, send)
    await JSONResponse([request.state.locale.language, request.state.locale.territory])(scope, receive, send)


class _User:
    """A user object exposing the preferred language under two different getter names."""

    def __init__(self, language: str | None) -> None:
        self.language = language

    def get_preferred_language(self) -> str | None:
        return self.language

    def preferred_locale(self) -> str | None:
        return self.language


def make_conn(*field_lines: str) -> HTTPConnection:
    """Build a connection carrying one `accept-language` field line per argument."""
    headers = [(b"accept-language", line.encode()) for line in field_lines]
    return HTTPConnection({"type": "http", "headers": headers})


def make_query_conn(query_string: str) -> HTTPConnection:
    """Build a connection with the given raw query string."""
    return HTTPConnection({"type": "http", "headers": [], "query_string": query_string.encode()})


def make_cookie_conn(cookie: str) -> HTTPConnection:
    """Build a connection carrying the given `cookie` field value."""
    return HTTPConnection({"type": "http", "headers": [(b"cookie", cookie.encode())]})


def make_user_conn(user: object) -> HTTPConnection:
    """Build a connection with an authenticated user in scope."""
    return HTTPConnection({"type": "http", "headers": [], "user": user})


class TestLocaleFromQuery:
    def test_reads_the_default_parameter(self) -> None:
        assert LocaleFromQuery()(make_query_conn("lang=be_BY")) == "be_BY"

    def test_reads_a_custom_parameter(self) -> None:
        assert LocaleFromQuery(query_param="locale")(make_query_conn("locale=be_BY")) == "be_BY"

    def test_returns_none_when_the_parameter_is_absent(self) -> None:
        """Absence is not a failure: the middleware moves on to the next selector."""
        assert LocaleFromQuery()(make_query_conn("locale=be_BY")) is None

    def test_returns_the_value_unvalidated(self) -> None:
        """Whatever the client sent is handed on as-is, nonsense included."""
        assert LocaleFromQuery()(make_query_conn("lang=not-a-locale")) == "not-a-locale"


class TestLocaleFromCookie:
    def test_reads_the_default_cookie(self) -> None:
        assert LocaleFromCookie()(make_cookie_conn("language=be_BY")) == "be_BY"

    def test_reads_a_custom_cookie(self) -> None:
        assert LocaleFromCookie("lang")(make_cookie_conn("lang=be_BY")) == "be_BY"

    def test_returns_none_when_the_cookie_is_absent(self) -> None:
        assert LocaleFromCookie()(make_cookie_conn("lang=be_BY")) is None


class TestLocaleFromUser:
    def test_calls_the_default_getter(self) -> None:
        assert LocaleFromUser()(make_user_conn(_User("be_BY"))) == "be_BY"

    def test_calls_a_custom_getter(self) -> None:
        assert LocaleFromUser(getter_method="preferred_locale")(make_user_conn(_User("be_BY"))) == "be_BY"

    def test_returns_none_when_the_getter_supplies_no_language(self) -> None:
        """A user who has expressed no preference is not an error."""
        assert LocaleFromUser()(make_user_conn(_User(None))) is None

    def test_returns_none_when_the_scope_has_no_user(self) -> None:
        """Unauthenticated requests skip the selector instead of raising on `conn.user`."""
        assert LocaleFromUser()(make_conn()) is None

    def test_returns_none_when_the_user_lacks_the_getter(self) -> None:
        """A user object from an auth backend that knows nothing about languages is simply skipped."""
        assert LocaleFromUser()(make_user_conn(object())) is None


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
        assert parse_accept_language("fr ; q=0.9 , be_BY") == (("be_BY", 1.0), ("fr", 0.9))

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

    def test_parses_a_header_at_the_length_limit_in_full(self) -> None:
        """Nothing is discarded while the field value stays within `MAX_HEADER_LENGTH`."""
        members = ["en"] + [f"l{i:03}" for i in range(99)]
        header = ",".join(members).ljust(MAX_HEADER_LENGTH, "x")
        assert len(header) == MAX_HEADER_LENGTH
        assert len(parse_accept_language(header)) == len(members)

    def test_discards_an_oversized_header_at_a_member_boundary(self) -> None:
        """An over-long field value is cut back to its last complete member.

        The straddling member is dropped whole rather than parsed from a fragment, so a truncated
        range is never mistaken for a preference the client expressed."""
        header = ",".join(["en"] + [f"l{i:03}" for i in range(200)])
        assert len(header) > MAX_HEADER_LENGTH

        parsed = parse_accept_language(header)
        assert len(parsed) < 201
        assert all(len(lang_range) in (2, 4) for lang_range, _ in parsed)
        assert header.startswith(",".join(lang_range for lang_range, _ in parsed))

    def test_discards_an_oversized_header_naming_a_single_member(self) -> None:
        """With no member boundary below the limit there is nothing safe to keep."""
        assert parse_accept_language("e" * (MAX_HEADER_LENGTH + 1)) == ()

    def test_keeps_the_wildcard_as_an_ordinary_range(self) -> None:
        """'*' is parsed as a range like any other, weight included."""
        assert parse_accept_language("*;q=0.2") == (("*", 0.2),)

    def test_keeps_duplicate_ranges(self) -> None:
        """A range repeated at two weights is returned twice.

        RFC 9110 12.5.4 does not forbid the repetition, and deciding which weight wins is a matching
        concern; `LocaleFromHeader` collapses duplicates to their highest weight before matching."""
        assert parse_accept_language("en;q=0.1, en;q=0.9") == (("en", 0.9), ("en", 0.1))

    def test_does_not_normalise_case(self) -> None:
        """Ranges are returned exactly as written; folding case is the matcher's job."""
        assert parse_accept_language("en-US;q=0.5") == (("en-US", 0.5),)


class TestLocaleFromHeader:
    def test_selects_the_best_acceptable_member_of_a_priority_list(self) -> None:
        """The highest-weighted member that resolves wins, not the first one written."""
        header = "en-US,en;q=0.9,ru-BY;q=0.8,ru;q=0.7,be-BY;q=0.6,be;q=0.5,pl;q=0.4,de;q=0.3"
        assert LocaleFromHeader(["be_BY"])(make_conn(header)) == "be_BY"

    @pytest.mark.parametrize("header", ("be-BY", "be_BY"))
    @pytest.mark.parametrize("configured", ("be-BY", "be_BY"))
    def test_accepts_either_subtag_separator(self, configured: str, header: str) -> None:
        """Either separator works, in the header and in the configured locales alike."""
        assert LocaleFromHeader([configured])(make_conn(header)) == "be_BY"

    @pytest.mark.parametrize(
        "header, expected",
        [
            ("de_CH, de_DE, de", "de_CH"),
            # ("de_DE, de", "de_DE"),
            # ("de", "de"),
        ],
    )
    def test_prefers_the_first_configured_locale_when_several_match_equally(self, header: str, expected: str) -> None:
        """Ranges matching equally well at the same weight are settled by the configured order."""
        assert LocaleFromHeader(["de_CH", "de_DE", "de"])(make_conn(header)) == expected

    @pytest.mark.parametrize(
        "header, expected",
        [
            ("de_CH, de_DE, de", "de_CH"),
            ("de_DE, de", "de_CH"),
            ("de", "de_CH"),
        ],
    )
    def test_widens_any_matching_range_to_the_only_supported_variant(self, header: str, expected: str) -> None:
        """However specific the German range, the sole supported German variant answers it."""
        assert LocaleFromHeader(["de_CH"])(make_conn(header)) == expected

    def test_combines_repeated_field_lines(self) -> None:
        """Repeated accept-language field lines form a single comma-joined value."""
        assert LocaleFromHeader(["be_BY", "fr"])(make_conn("fr;q=0.5", "be")) == "be_BY"

    def test_prefers_an_exact_match_over_truncation(self) -> None:
        """Lookup returns the most specific acceptable locale, not the shortest."""
        assert LocaleFromHeader(["en", "en_US"])(make_conn("en-US")) == "en_US"

    def test_truncates_a_range_to_a_supported_language(self) -> None:
        """A range more specific than anything supported is truncated from the right."""
        assert LocaleFromHeader(["fr", "de"])(make_conn("de-DE")) == "de"

    def test_does_not_truncate_when_the_full_range_is_supported(self) -> None:
        """Truncation is a fallback, not a first move: an exact match ends the search."""
        assert LocaleFromHeader(["fr", "de", "de_DE"])(make_conn("de-DE")) == "de_DE"

    @pytest.mark.parametrize("locales", (["zh", "zh_Hant"], ["zh_Hant", "zh"]))
    def test_truncates_one_subtag_at_a_time(self, locales: list[str]) -> None:
        """Truncation is progressive, so a supported intermediate variant is not skipped."""
        assert LocaleFromHeader(locales)(make_conn("zh-Hant-CN")) == "zh_Hant"

    def test_truncation_drops_singleton_subtags(self) -> None:
        """Single-character subtags are removed together with their trailing subtag."""
        assert LocaleFromHeader(["zh", "fr"])(make_conn("zh-x-pig")) == "zh"

    def test_range_of_only_a_private_use_sequence_names_no_language(self) -> None:
        """Truncating away the singleton can leave nothing at all, which is not a match.

        RFC 4647 2.1 admits 'x-pig' as a language-range, but the private-use 'x' goes with its
        trailing subtag and nothing remains to compare, so the search moves on to the next range."""
        assert LocaleFromHeader(["en", "zh"])(make_conn("x-pig")) is None
        assert LocaleFromHeader(["en", "zh"])(make_conn("x-pig,zh;q=0.5")) == "zh"

    def test_resolves_each_range_fully_before_the_next(self) -> None:
        """A range is truncated to exhaustion before a lower-priority range is consulted."""
        assert LocaleFromHeader(["ca", "es", "en"])(make_conn("ca-ES,es;q=0.9,en;q=0.8")) == "ca"

    def test_widens_a_range_to_a_supported_variant(self) -> None:
        """A range broader than anything supported still resolves, by widening."""
        assert LocaleFromHeader(["fr", "be_BY"])(make_conn("be")) == "be_BY"

    def test_refusal_covers_what_the_range_matches_and_nothing_broader(self) -> None:
        """A q=0 range refuses only the locales it covers."""
        header = "en;q=1, en-gb;q=0"
        assert LocaleFromHeader(["en_GB", "fr"])(make_conn(header)) is None
        assert LocaleFromHeader(["en", "fr"])(make_conn(header)) == "en"

    def test_does_not_truncate_past_an_exclusion(self) -> None:
        """Truncation may not land on a locale the client refused."""
        assert LocaleFromHeader(["ca", "fr"])(make_conn("ca-ES,ca;q=0")) is None

    def test_skips_a_refused_candidate_and_keeps_looking_in_the_same_tier(self) -> None:
        """A refusal rejects one candidate, not the whole match tier."""
        assert LocaleFromHeader(["de_CH", "de_AT"])(make_conn("de-DE;q=1, de-ch;q=0")) == "de_AT"


class TestWildcardRange:
    @pytest.mark.parametrize(
        ("locales", "header", "expected"),
        (
            (["en"], "*, en;q=0.5", "en"),
            (["es"], "*, es;q=0.1", "es"),
        ),
    )
    def test_yields_when_every_supported_locale_is_named(self, locales: list[str], header: str, expected: str) -> None:
        """An empty territory makes '*' step aside rather than end the search."""
        assert LocaleFromHeader(locales)(make_conn(header)) == expected

    def test_refused_wildcard_leaves_only_the_named_ranges(self) -> None:
        """'*;q=0' inverts the field into a whitelist."""
        assert LocaleFromHeader(["en", "es"])(make_conn("*;q=0, es;q=0.1")) == "es"


def test_locale_middleware_supports_language_shortcuts() -> None:
    """It should properly detect locale when user defines list of supported locales without region."""
    client = TestClient(LocaleMiddleware(app, locales=["be"]))
    assert client.get("/?lang=be_BY").json() == ["be", None]


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


def test_get_text_direction_from_string() -> None:
    assert get_text_direction("ar") == "rtl"
    assert get_text_direction("he") == "rtl"
    assert get_text_direction("en") == "ltr"


def test_get_text_direction_from_locale_object() -> None:
    assert get_text_direction(Locale.parse("ar_SA")) == "rtl"


def test_get_text_direction_uses_current_locale() -> None:
    with switch_locale("ar"):
        assert get_text_direction() == "rtl"
    with switch_locale("be_BY"):
        assert get_text_direction() == "ltr"


def test_locale_middleware_sets_text_direction_state() -> None:
    async def direction_app(scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive, send)
        await JSONResponse(request.state.text_direction)(scope, receive, send)

    client = TestClient(LocaleMiddleware(direction_app, locales=["en", "ar"], default_locale="en"))
    assert client.get("/?lang=ar").json() == "rtl"
    assert client.get("/?lang=en").json() == "ltr"
