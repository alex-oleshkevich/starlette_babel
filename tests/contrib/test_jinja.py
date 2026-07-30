import datetime
import jinja2
import pathlib
import pytest
import typing

from starlette_babel import Translator, switch_locale, switch_timezone
from starlette_babel.contrib.jinja import configure_jinja_env

LOCALE_DIR = pathlib.Path(__file__).parent.parent / "locales"
translator = Translator([LOCALE_DIR])
jinja_env = jinja2.Environment()
configure_jinja_env(jinja_env, translator=translator)
christmas = datetime.datetime(2022, 12, 25, 12, 30, 59)


@pytest.fixture(autouse=True)
def set_locale() -> typing.Iterator[None]:
    with switch_locale("be"), switch_timezone("UTC"):
        yield


def test_translates_singular() -> None:
    template = jinja_env.from_string('{{ _("Hello") }}')
    assert template.render() == "Вітаем"


def test_translates_plural() -> None:
    template = jinja_env.from_string('{{ _p("{count} apple", "{count} apples", 1) }}')
    assert template.render() == "1 яблык"


def test_formats_datetime() -> None:
    template = jinja_env.from_string("{{ christmas|datetime }}")
    assert template.render(christmas=christmas) == "25 сне 2022\u202fг., 12:30:59"


def test_formats_date() -> None:
    template = jinja_env.from_string("{{ christmas|date }}")
    assert template.render(christmas=christmas) == "25 сне 2022\u202fг."


def test_formats_time() -> None:
    template = jinja_env.from_string("{{ christmas|time }}")
    assert template.render(christmas=christmas) == "12:30:59"


def test_formats_timedelta() -> None:
    delta = datetime.timedelta(seconds=10)
    template = jinja_env.from_string("{{ delta|timedelta }}")
    assert template.render(delta=delta) == "10 секунд"


def test_formats_number() -> None:
    template = jinja_env.from_string("{{ number|number }}")
    assert template.render(number=100500.42) == "100 500,42"


def test_formats_currency() -> None:
    template = jinja_env.from_string('{{ number|currency("BYN") }}')
    assert template.render(number=100500.42) == "100 500,42 Br"


def test_formats_percent() -> None:
    template = jinja_env.from_string("{{ number|percent }}")
    assert template.render(number=42.95) == "4 295 %"


def test_formats_scientific() -> None:
    template = jinja_env.from_string("{{ number|scientific }}")
    assert template.render(number=1234567) == "1,234567E6"


def test_translates_with_context() -> None:
    template = jinja_env.from_string('{{ _c("month", "May") }} / {{ _c("verb", "May") }}')
    assert template.render() == "Травень / Можа"


def test_translates_plural_with_context() -> None:
    template = jinja_env.from_string('{{ _cp("fruit", "{count} apple", "{count} apples", 2) }}')
    assert template.render() == "2 садавіны"


def test_trans_tag_with_context() -> None:
    """Jinja's i18n extension picks up pgettext from the translations object."""
    template = jinja_env.from_string('{% trans "verb" %}May{% endtrans %}')
    assert template.render() == "Можа"


def test_exposes_locale_globals() -> None:
    template = jinja_env.from_string("{{ language() }}|{{ locale() }}|{{ text_direction() }}")
    assert template.render() == "be|be|ltr"


def test_text_direction_global_for_rtl_locale() -> None:
    with switch_locale("ar"):
        template = jinja_env.from_string("{{ text_direction() }}")
        assert template.render() == "rtl"


def test_exposes_name_globals() -> None:
    template = jinja_env.from_string("{{ month_names()[12] }}|{{ day_names()[0] }}")
    assert template.render() == "снежня|панядзелак"


def test_exposes_currency_globals() -> None:
    template = jinja_env.from_string('{{ currency_symbol("USD") }}|{{ currency_name("USD", 2) }}')
    assert template.render() == "$|долары ЗША"


def test_formats_interval() -> None:
    template = jinja_env.from_string("{{ start|interval(end) }}")
    start = datetime.datetime(2022, 12, 25, 12, 30)
    end = datetime.datetime(2022, 12, 26, 12, 30)
    assert template.render(start=start, end=end)


def test_formats_skeleton() -> None:
    template = jinja_env.from_string('{{ christmas|skeleton("yMMMd") }}')
    assert template.render(christmas=christmas) == "25 сне 2022"


def test_formats_decimal() -> None:
    template = jinja_env.from_string("{{ number|decimal }}")
    assert template.render(number=100500.42) == "100\u00a0500,42"


def test_formats_compact_decimal() -> None:
    template = jinja_env.from_string("{{ number|compact_decimal(fraction_digits=1) }}")
    assert template.render(number=1_200_000) == "1,2\u00a0млн"


def test_formats_compact_currency() -> None:
    with switch_locale("en_US"):
        template = jinja_env.from_string('{{ number|compact_currency("USD", fraction_digits=1) }}')
        assert template.render(number=1_200_000) == "$1.2M"


def test_formats_unit() -> None:
    template = jinja_env.from_string('{{ 5|unit("length-kilometer") }}')
    assert template.render() == "5 кіламетраў"


def test_formats_list() -> None:
    template = jinja_env.from_string("{{ items|format_list }}")
    assert template.render(items=["a", "b", "c"]) == "a, b і c"


def test_format_list_does_not_shadow_builtin_list_filter() -> None:
    """Jinja ships its own `list` filter — ours must not replace it."""
    template = jinja_env.from_string("{{ 'abc'|list }}")
    assert template.render() == "['a', 'b', 'c']"
