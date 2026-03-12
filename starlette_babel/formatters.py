"""
Date, time, numbers, and currency formatters.

This module inspired/based on Flask-Babel.
"""

import datetime
import decimal
import typing

from babel import Locale, dates, numbers

from starlette_babel.locale import get_locale
from starlette_babel.timezone import get_timezone

_DateTimeFormats = typing.Literal["short", "medium", "long", "full"]
_TimeDeltaFormats = typing.Literal["narrow", "short", "long"]


def parse_locale(locale: str | Locale | None) -> Locale:
    """
    Parse locale from string, Locale object, or None. If None passed then current global locale returned.

    Part of internal API.
    """
    if locale is None:
        return get_locale()
    if isinstance(locale, str):
        return Locale.parse(locale)
    return locale


def format_datetime(
    dt: datetime.datetime, format: _DateTimeFormats = "medium", rebase: bool = True, locale: str | None = None
) -> str:
    tz = get_timezone() if rebase else None
    return dates.format_datetime(dt, format=format, tzinfo=tz, locale=parse_locale(locale))


def format_date(
    date: datetime.date | datetime.datetime, format: _DateTimeFormats = "medium", locale: str | None = None
) -> str:
    return dates.format_date(date, format=format, locale=parse_locale(locale))


def format_time(
    time: datetime.time | datetime.datetime,
    format: _DateTimeFormats = "medium",
    rebase: bool = True,
    locale: str | None = None,
) -> str:
    """Format a time value.

    When `rebase=True` and a `datetime.time` is passed, the time is rebased to the current user timezone.
    Note: rebasing a `datetime.time` without a date context is DST-ambiguous — the UTC offset used
    may not be correct during DST transitions. Pass a full `datetime.datetime` to avoid this.
    """
    if rebase:
        if isinstance(time, datetime.time):
            time = datetime.datetime.now(tz=datetime.timezone.utc).replace(
                hour=time.hour,
                minute=time.minute,
                second=time.second,
                microsecond=time.microsecond,
                tzinfo=time.tzinfo,
                fold=time.fold,
            )
        return dates.format_time(time, format=format, tzinfo=get_timezone(), locale=parse_locale(locale))
    return dates.format_time(time, format=format, locale=parse_locale(locale))


def format_timedelta(
    timedelta: datetime.timedelta,
    granularity: typing.Literal["year", "month", "week", "day", "hour", "minute", "second"] = "second",
    threshold: float = 0.85,
    add_direction: bool = False,
    format: _TimeDeltaFormats = "long",
    locale: str | None = None,
) -> str:
    return dates.format_timedelta(
        timedelta,
        granularity=granularity,
        format=format,
        locale=parse_locale(locale),
        threshold=threshold,
        add_direction=add_direction,
    )


def format_interval(
    start: typing.Union[datetime.datetime, datetime.date, datetime.time],
    end: typing.Union[datetime.datetime, datetime.date, datetime.time],
    skeleton: str | None = None,
    fuzzy: bool = True,
    rebase: bool = True,
    locale: str | None = None,
) -> str:
    if type(start) is not type(end):
        raise TypeError('"start" and "end" arguments must be of the same type.')
    extra_kwargs = {}
    if rebase:
        extra_kwargs["tzinfo"] = get_timezone()
    return dates.format_interval(
        start, end, skeleton=skeleton, fuzzy=fuzzy, locale=parse_locale(locale), **extra_kwargs
    )


def format_number(
    number: float,
    decimal_quantization: bool = True,
    group_separator: bool = True,
    locale: str | None = None,
) -> str:
    value = numbers.format_decimal(
        number,
        locale=parse_locale(locale),
        decimal_quantization=decimal_quantization,
        group_separator=group_separator,
    )
    return typing.cast(str, value)


def format_currency(
    number: float | decimal.Decimal | str | int,
    currency: str,
    format: str | None = None,
    currency_digits: bool = True,
    format_type: typing.Literal["name", "standard", "accounting"] = "standard",
    decimal_quantization: bool = True,
    group_separator: bool = True,
    locale: str | None = None,
) -> str:
    value = numbers.format_currency(
        number,
        currency,
        format=format,
        locale=parse_locale(locale),
        currency_digits=currency_digits,
        format_type=format_type,
        decimal_quantization=decimal_quantization,
        group_separator=group_separator,
    )
    return value


def format_percent(
    number: float | int | decimal.Decimal | str,
    format: str | None = None,
    decimal_quantization: bool = True,
    group_separator: bool = True,
    locale: str | None = None,
) -> str:
    value = numbers.format_percent(
        number,
        format=format,
        locale=parse_locale(locale),
        decimal_quantization=decimal_quantization,
        group_separator=group_separator,
    )
    return value


def format_scientific(
    number: float | int | decimal.Decimal | str,
    format: str | None = None,
    decimal_quantization: bool = True,
    locale: str | None = None,
) -> str:
    value = numbers.format_scientific(
        number,
        format=format,
        decimal_quantization=decimal_quantization,
        locale=parse_locale(locale),
    )
    return value


def format_compact_decimal(
    number: float | int | decimal.Decimal,
    *,
    fraction_digits: int = 0,
    format_type: typing.Literal["short", "long"] = "short",
    locale: str | None = None,
) -> str:
    """Format a number in compact notation (e.g. 1 200 000 → 1M or 1 million).

    Example:
        ```python
        from starlette_babel import format_compact_decimal, set_locale

        set_locale('en_US')
        format_compact_decimal(1_200_000)                      # '1M'
        format_compact_decimal(1_200_000, fraction_digits=1)   # '1.2M'
        format_compact_decimal(1_200_000, format_type='long')  # '1 million'
        ```
    """
    value = numbers.format_compact_decimal(
        number,  # type: ignore[arg-type]
        fraction_digits=fraction_digits,
        format_type=format_type,
        locale=parse_locale(locale),
    )
    return str(value)


def parse_decimal(
    string: str,
    locale: str | None = None,
) -> decimal.Decimal:
    """Parse a locale-formatted decimal string into a Decimal.

    Example:
        ```python
        from starlette_babel import parse_decimal, set_locale

        set_locale('de_DE')
        parse_decimal('1.234,56')  # Decimal('1234.56')
        ```
    """
    return numbers.parse_decimal(string, locale=parse_locale(locale))


def parse_number(
    string: str,
    locale: str | None = None,
) -> int:
    """Parse a locale-formatted integer string into an int.

    Example:
        ```python
        from starlette_babel import parse_number, set_locale

        set_locale('de_DE')
        parse_number('1.234')  # 1234
        ```
    """
    return numbers.parse_number(string, locale=parse_locale(locale))
