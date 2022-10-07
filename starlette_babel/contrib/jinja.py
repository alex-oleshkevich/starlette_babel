import jinja2

from starlette_babel import formatters, get_locale
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


def configure_jinja_env(jinja_env: jinja2.Environment, translator: Translator | None = None) -> None:
    """Enhance Jinja2 environment with i18n related features."""
    base_translator = translator or get_translator()
    translator_ = _LocaleAwareTranslator(base_translator)

    jinja_env.globals.update(
        {
            "_": translator_.gettext,
            "_p": translator_.ngettext,
        }
    )
    jinja_env.filters.update(
        {
            "datetime": formatters.format_datetime,
            "date": formatters.format_date,
            "time": formatters.format_time,
            "timedelta": formatters.format_timedelta,
            "number": formatters.format_number,
            "currency": formatters.format_currency,
            "percent": formatters.format_percent,
            "scientific": formatters.format_scientific,
        }
    )
    jinja_env.add_extension("jinja2.ext.i18n")
    jinja_env.install_gettext_translations(translator_)  # type: ignore[attr-defined]
