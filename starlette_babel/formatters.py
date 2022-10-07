"""
Date, time, numbers, and currency formatters.

This module inspired/based on Flask-Babel.
"""
import datetime
import typing
from babel import Locale, dates, numbers

from starlette_babel.locale import get_locale
from starlette_babel.timezone import get_timezone, to_user_timezone

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
        return typing.cast(Locale, Locale.parse(locale))
    return locale


def format_datetime(
    dt: datetime.datetime, format: _DateTimeFormats = "medium", rebase: bool = True, locale: str | None = None
) -> str:
    if rebase:
        dt = to_user_timezone(dt)
    return dates.format_datetime(dt, format=format, locale=parse_locale(locale))


def format_date(date: datetime.datetime, format: _DateTimeFormats = "medium", locale: str | None = None) -> str:
    return dates.format_date(date, format=format, locale=parse_locale(locale))


def format_time(
    time: datetime.datetime, format: _DateTimeFormats = "medium", rebase: bool = True, locale: str | None = None
) -> str:
    if rebase:
        time = to_user_timezone(time)
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
    assert type(start) == type(end), '"start" and "end" arguments must be of the same type.'
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
    number: float,
    currency: str,
    format: str | None = None,
    currency_digits: bool = True,
    format_type: str = "standard",
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
    return typing.cast(str, value)


def format_percent(
    number: float,
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
    return typing.cast(str, value)


def format_scientific(
    number: float,
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
    return typing.cast(str, value)
