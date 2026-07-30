import datetime

import jinja2

from starlette_babel import formatters, get_language, get_locale, get_text_direction
from starlette_babel.translator import Translator, get_translator


class _LocaleAwareTranslator:
    def __init__(self, base_translator: Translator) -> None:
        self.translator = base_translator

    def gettext(self, msgid: str, domain: str = "messages", locale: str | None = None) -> str:
        locale = str(locale or get_locale())
        return self.translator.gettext(msgid, locale=locale, domain=domain)

    def ngettext(
        self,
        singular: str,
        plural: str,
        count: int,
        locale: str | None = None,
        domain: str = "messages",
    ) -> str:
        locale = str(locale or get_locale())
        return self.translator.ngettext(singular, plural, count, locale=locale, domain=domain)

    def pgettext(self, context: str, msgid: str, domain: str = "messages", locale: str | None = None) -> str:
        locale = str(locale or get_locale())
        return self.translator.pgettext(context, msgid, locale=locale, domain=domain)

    def npgettext(
        self,
        context: str,
        singular: str,
        plural: str,
        count: int,
        locale: str | None = None,
        domain: str = "messages",
    ) -> str:
        locale = str(locale or get_locale())
        return self.translator.npgettext(context, singular, plural, count, locale=locale, domain=domain)


def _skeleton_filter(
    dt: datetime.datetime | datetime.time,
    skeleton: str,
    fuzzy: bool = True,
    rebase: bool = True,
    locale: str | None = None,
) -> str:
    """Adapt `format_skeleton` to filter argument order: the filtered value comes first."""
    return formatters.format_skeleton(skeleton, dt, fuzzy=fuzzy, rebase=rebase, locale=locale)


def configure_jinja_env(jinja_env: jinja2.Environment, translator: Translator | None = None) -> None:
    """Enhance Jinja2 environment with i18n related features."""
    base_translator = translator or get_translator()
    translator_ = _LocaleAwareTranslator(base_translator)

    jinja_env.globals.update(
        {
            "_": translator_.gettext,
            "_p": translator_.ngettext,
            "_c": translator_.pgettext,
            "_cp": translator_.npgettext,
            "locale": get_locale,
            "language": get_language,
            "text_direction": get_text_direction,
            "month_names": formatters.get_month_names,
            "day_names": formatters.get_day_names,
            "currency_symbol": formatters.get_currency_symbol,
            "currency_name": formatters.get_currency_name,
        }
    )
    jinja_env.filters.update(
        {
            "datetime": formatters.format_datetime,
            "date": formatters.format_date,
            "time": formatters.format_time,
            "timedelta": formatters.format_timedelta,
            "interval": formatters.format_interval,
            "skeleton": _skeleton_filter,
            "number": formatters.format_number,
            "decimal": formatters.format_decimal,
            "compact_decimal": formatters.format_compact_decimal,
            "currency": formatters.format_currency,
            "compact_currency": formatters.format_compact_currency,
            "percent": formatters.format_percent,
            "scientific": formatters.format_scientific,
            "unit": formatters.format_unit,
            # not `list`: Jinja ships a builtin filter under that name.
            "format_list": formatters.format_list,
        }
    )
    jinja_env.add_extension("jinja2.ext.i18n")
    jinja_env.install_gettext_translations(translator_)  # type: ignore[attr-defined]
