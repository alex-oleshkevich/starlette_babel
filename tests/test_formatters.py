import datetime
import pytest
import typing
from babel import Locale

from starlette_babel import switch_locale, switch_timezone
from starlette_babel.formatters import (
    format_currency,
    format_date,
    format_datetime,
    format_interval,
    format_number,
    format_percent,
    format_scientific,
    format_time,
    format_timedelta,
    parse_locale,
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
    assert format_datetime(christmas, "medium", False) == "25 сне 2022 г., 12:30:59"
    assert format_datetime(christmas, "long", False) == "25 снежня 2022 г. у 12:30:59 UTC"
    assert (
        format_datetime(christmas, "full", False)
        == "нядзеля, 25 снежня 2022 г. у 12:30:59, Універсальны каардынаваны час"
    )


def test_format_datetime_rebases_timezone(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_datetime(christmas, "short", True) == "25.12.22, 15:30"
    assert format_datetime(christmas, "medium", True) == "25 сне 2022 г., 15:30:59"
    assert format_datetime(christmas, "long", True) == "25 снежня 2022 г. у 15:30:59 +0300"
    assert format_datetime(christmas, "full", True) == "нядзеля, 25 снежня 2022 г. у 15:30:59, Маскоўскі стандартны час"


def test_format_date(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_date(christmas, "short") == "25.12.22"
    assert format_date(christmas, "medium") == "25 сне 2022 г."
    assert format_date(christmas, "long") == "25 снежня 2022 г."
    assert format_date(christmas, "full") == "нядзеля, 25 снежня 2022 г."


def test_format_time(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_time(christmas, "short", False) == "12:30"
    assert format_time(christmas, "medium", False) == "12:30:59"
    assert format_time(christmas, "long", False) == "12:30:59 UTC"
    assert format_time(christmas, "full", False) == "12:30:59, Універсальны каардынаваны час"


def test_format_time_rebases_timezone(
    bel_tz: typing.Generator[None, None, None], bel_locale: typing.Generator[None, None, None]
) -> None:
    assert format_time(christmas, "short", True) == "15:30"
    assert format_time(christmas, "medium", True) == "15:30:59"
    assert format_time(christmas, "long", True) == "15:30:59 +0300"
    assert format_time(christmas, "full", True) == "15:30:59, Маскоўскі стандартны час"


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
        == "1 сту 2022 г. – 1 лют 2022 г."
    )
    assert (
        format_interval(datetime.datetime(2022, 1, 1, 0, 0, 0), datetime.datetime(2022, 2, 1, 0, 0, 0), rebase=False)
        == "1 сту 2022 г., 00:00:00 – 1 лют 2022 г., 00:00:00"
    )

    assert (
        format_interval(datetime.datetime(2022, 1, 1, 0, 0, 0), datetime.datetime(2022, 2, 1, 0, 0, 0), rebase=True)
        == "1 сту 2022 г., 03:00:00 – 1 лют 2022 г., 03:00:00"
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
