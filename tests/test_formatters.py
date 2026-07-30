import datetime
import typing

import pytest
from babel import Locale

from starlette_babel import switch_locale, switch_timezone
from starlette_babel.formatters import (
    format_compact_currency,
    format_compact_decimal,
    format_currency,
    format_date,
    format_datetime,
    format_decimal,
    format_interval,
    format_list,
    format_number,
    format_percent,
    format_scientific,
    format_skeleton,
    format_time,
    format_timedelta,
    format_unit,
    get_currency_name,
    get_currency_symbol,
    get_day_names,
    get_month_names,
    parse_date,
    parse_decimal,
    parse_locale,
    parse_number,
    parse_time,
)

christmas = datetime.datetime(2022, 12, 25, 12, 30, 59)


@pytest.fixture
def bel_tz() -> typing.Generator[None, None, None]:
    with switch_timezone("Europe/Minsk"):
        yield


@pytest.fixture
def bel_locale() -> typing.Generator[None, None, None]:
    with switch_locale("be_BY"):
        yield


def test_parse_locale_from_string() -> None:
    assert parse_locale("be_BY").language == "be"


def test_parse_locale_from_locale() -> None:
    assert parse_locale(Locale.parse("be_BY")).language == "be"


def test_parse_locale_from_none() -> None:
    with switch_locale("be_BY"):
        assert parse_locale(None).language == "be"


def test_format_datetime(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_datetime(christmas, "short", False) == "25.12.22, 12:30"
    assert format_datetime(christmas, "medium", False) == "25 сне 2022\u202fг., 12:30:59"
    assert format_datetime(christmas, "long", False) == "25 снежня 2022\u202fг., 12:30:59 UTC"
    assert (
        format_datetime(christmas, "full", False)
        == "нядзеля, 25 снежня 2022\u202fг., 12:30:59, Універсальны каардынаваны час"
    )


def test_format_datetime_rebases_timezone(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_datetime(christmas, "short", True) == "25.12.22, 15:30"
    assert format_datetime(christmas, "medium", True) == "25 сне 2022\u202fг., 15:30:59"
    assert format_datetime(christmas, "long", True) == "25 снежня 2022\u202fг., 15:30:59 +0300"
    assert (
        format_datetime(christmas, "full", True)
        == "нядзеля, 25 снежня 2022\u202fг., 15:30:59, Маскоўскі стандартны час"
    )


def test_format_date(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_date(christmas, "short") == "25.12.22"
    assert format_date(christmas, "medium") == "25 сне 2022\u202fг."
    assert format_date(christmas, "long") == "25 снежня 2022\u202fг."
    assert format_date(christmas, "full") == "нядзеля, 25 снежня 2022\u202fг."


def test_format_time(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_time(christmas, "short", False) == "12:30"
    assert format_time(christmas, "medium", False) == "12:30:59"
    assert format_time(christmas, "long", False) == "12:30:59 UTC"
    assert format_time(christmas, "full", False) == "12:30:59, Універсальны каардынаваны час"

    naive_time = datetime.time(12, 30, 59)
    assert format_time(naive_time, "medium", False) == "12:30:59"


def test_format_time_rebases_timezone(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_time(christmas, "short", True) == "15:30"
    assert format_time(christmas, "medium", True) == "15:30:59"
    assert format_time(christmas, "long", True) == "15:30:59 +0300"
    assert format_time(christmas, "full", True) == "15:30:59, Маскоўскі стандартны час"

    naive_time = datetime.time(12, 30, 59)
    assert format_time(naive_time, "medium", True) == "15:30:59"


def test_format_timedelta(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_timedelta(datetime.timedelta(seconds=10), format="long", granularity="second") == "10 секунд"
    assert format_timedelta(datetime.timedelta(seconds=55), format="long", granularity="second") == "1 хвіліна"
    assert (
        format_timedelta(datetime.timedelta(seconds=55), format="long", granularity="second", threshold=0.99)
        == "55 секунд"
    )
    assert (
        format_timedelta(datetime.timedelta(seconds=55), format="long", granularity="second", add_direction=True)
        == "праз 1 хвіліну"
    )

    assert format_timedelta(datetime.timedelta(minutes=10), format="narrow", granularity="second") == "10 хв"
    assert format_timedelta(datetime.timedelta(minutes=10), format="short", granularity="minute") == "10 хв"
    assert format_timedelta(datetime.timedelta(minutes=10), format="long", granularity="second") == "10 хвілін"


def test_format_interval(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_interval(datetime.time(8, 15), datetime.time(9, 0), rebase=False) == "08:15:00 – 09:00:00"
    assert format_interval(datetime.time(8, 15), datetime.time(9, 0), skeleton="Hm", rebase=False) == "08.15–09.00"
    assert (
        format_interval(datetime.time(8, 15), datetime.time(9, 0), fuzzy=False, rebase=False) == "08:15:00 – 09:00:00"
    )
    assert format_interval(datetime.time(8, 15), datetime.time(9, 0), rebase=True) == "08:15:00 – 09:00:00"

    assert (
        format_interval(datetime.date(2022, 1, 1), datetime.date(2022, 2, 1), rebase=False)
        == "1 сту 2022\u202fг. – 1 лют 2022\u202fг."
    )
    assert (
        format_interval(datetime.datetime(2022, 1, 1, 0, 0, 0), datetime.datetime(2022, 2, 1, 0, 0, 0), rebase=False)
        == "1 сту 2022\u202fг., 00:00:00 – 1 лют 2022\u202fг., 00:00:00"
    )

    assert (
        format_interval(datetime.datetime(2022, 1, 1, 0, 0, 0), datetime.datetime(2022, 2, 1, 0, 0, 0), rebase=True)
        == "1 сту 2022\u202fг., 03:00:00 – 1 лют 2022\u202fг., 03:00:00"
    )


def test_format_number(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_number(100500.42, decimal_quantization=True, group_separator=True) == "100 500,42"
    assert format_number(100500.42, decimal_quantization=False, group_separator=True) == "100 500,42"
    assert format_number(100500.42, decimal_quantization=False, group_separator=False) == "100500,42"
    assert format_number(3.1415, decimal_quantization=False, group_separator=False) == "3,1415"
    assert format_number(3.1415, decimal_quantization=True, group_separator=False) == "3,142"


def test_format_currency(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert (
        format_currency(
            100500.42, currency="BYN", currency_digits=True, decimal_quantization=True, group_separator=True
        )
        == "100 500,42 Br"
    )
    assert (
        format_currency(
            100500.42,
            currency="BYN",
            currency_digits=True,
            format="¤¤ #,##0.00",
            decimal_quantization=True,
            group_separator=True,
        )
        == "BYN 100 500,42"
    )


def test_format_percent(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_percent(42.95, decimal_quantization=True, group_separator=True) == "4 295 %"
    assert format_percent(42.95, format="#,##0‰", decimal_quantization=True, group_separator=True) == "42 950‰"


def test_format_scientific(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_scientific(1234567, decimal_quantization=True) == "1,234567E6"
    assert format_scientific(1234567, format="##0.##E00", decimal_quantization=True) == "1,23E06"


def test_format_compact_decimal(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_compact_decimal(1_200_000) == "1\xa0млн"
    assert format_compact_decimal(1_200_000, fraction_digits=1) == "1,2\xa0млн"
    with switch_locale("en_US"):
        assert format_compact_decimal(1_200_000) == "1M"
        assert format_compact_decimal(1_200_000, fraction_digits=1) == "1.2M"
        assert format_compact_decimal(1_200_000, format_type="long") == "1 million"


def test_parse_decimal(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    import decimal as _decimal

    assert parse_decimal("100\xa0500,42") == _decimal.Decimal("100500.42")
    with switch_locale("en_US"):
        assert parse_decimal("100,500.42") == _decimal.Decimal("100500.42")


def test_parse_number(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert parse_number("100\xa0500") == 100500
    with switch_locale("en_US"):
        assert parse_number("100,500") == 100500


def test_format_interval_raises_for_type_mismatch(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    with pytest.raises(TypeError, match="same type"):
        format_interval(datetime.time(8, 15), datetime.date(2022, 1, 1))


def test_format_skeleton(bel_locale: typing.Generator[None, None, None]) -> None:
    assert format_skeleton("yMMMd", christmas, rebase=False) == "25 сне 2022"
    with switch_locale("en_US"):
        assert format_skeleton("yMMMd", christmas, rebase=False) == "Dec 25, 2022"


def test_format_skeleton_rebases_to_user_timezone(bel_locale: typing.Generator[None, None, None]) -> None:
    with switch_timezone("Europe/Minsk"):
        assert format_skeleton("Hm", christmas, rebase=True) == "15:30"
    with switch_timezone("UTC"):
        assert format_skeleton("Hm", christmas, rebase=True) == "12:30"


def test_format_decimal(bel_locale: typing.Generator[None, None, None]) -> None:
    assert format_decimal(12345.678) == "12 345,678"
    assert format_decimal(12345.678, group_separator=False) == "12345,678"


def test_format_number_matches_format_decimal(bel_locale: typing.Generator[None, None, None]) -> None:
    """`format_number` is kept as an alias and must not drift from `format_decimal`."""
    assert format_number(12345.678) == format_decimal(12345.678)


def test_format_compact_currency(bel_locale: typing.Generator[None, None, None]) -> None:
    with switch_locale("en_US"):
        assert format_compact_currency(1_200_000, "USD", fraction_digits=1) == "$1.2M"
        assert format_compact_currency(1_200_000, "USD") == "$1M"


def test_get_currency_symbol(bel_locale: typing.Generator[None, None, None]) -> None:
    assert get_currency_symbol("USD") == "$"
    with switch_locale("en_US"):
        assert get_currency_symbol("USD") == "$"


def test_get_currency_name(bel_locale: typing.Generator[None, None, None]) -> None:
    assert get_currency_name("USD", 2) == "долары ЗША"
    with switch_locale("en_US"):
        assert get_currency_name("USD", 2) == "US dollars"


def test_format_unit(bel_locale: typing.Generator[None, None, None]) -> None:
    assert format_unit(5, "length-kilometer") == "5 кіламетраў"
    assert format_unit(5, "length-kilometer", length="short") == "5 км"
    with switch_locale("en_US"):
        assert format_unit(5, "length-kilometer") == "5 kilometers"


def test_format_list(bel_locale: typing.Generator[None, None, None]) -> None:
    assert format_list(["a", "b", "c"]) == "a, b і c"
    assert format_list(["a", "b", "c"], style="or") == "a, b ці c"
    with switch_locale("en_US"):
        assert format_list(["a", "b", "c"]) == "a, b, and c"
        assert format_list(["a", "b", "c"], style="or") == "a, b, or c"


def test_get_month_names(bel_locale: typing.Generator[None, None, None]) -> None:
    assert get_month_names()[12] == "снежня"
    with switch_locale("en_US"):
        assert get_month_names()[12] == "December"
        assert get_month_names("abbreviated")[12] == "Dec"


def test_get_day_names(bel_locale: typing.Generator[None, None, None]) -> None:
    assert get_day_names()[0] == "панядзелак"
    with switch_locale("en_US"):
        assert get_day_names()[0] == "Monday"


def test_parse_date(bel_locale: typing.Generator[None, None, None]) -> None:
    assert parse_date("25.12.2022") == datetime.date(2022, 12, 25)
    with switch_locale("en_US"):
        assert parse_date("12/25/22") == datetime.date(2022, 12, 25)


def test_parse_time(bel_locale: typing.Generator[None, None, None]) -> None:
    assert parse_time("15:30:00") == datetime.time(15, 30)


def test_formatters_use_explicit_locale_over_current(bel_locale: typing.Generator[None, None, None]) -> None:
    """Every formatter honours an explicit `locale` argument regardless of the active locale."""
    assert format_list(["a", "b"], locale="en_US") == "a and b"
    assert format_unit(5, "length-kilometer", locale="en_US") == "5 kilometers"
    assert format_decimal(1234.5, locale="en_US") == "1,234.5"
    assert get_month_names(locale="en_US")[12] == "December"
