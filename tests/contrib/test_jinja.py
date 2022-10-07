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
    assert template.render(christmas=christmas) == "25 сне 2022 г., 12:30:59"


def test_formats_date() -> None:
    template = jinja_env.from_string("{{ christmas|date }}")
    assert template.render(christmas=christmas) == "25 сне 2022 г."


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
