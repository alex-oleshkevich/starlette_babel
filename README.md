# Starlette Babel

Provides translations, formatters, and timezone support for Starlette application by integrating Babel library.

![PyPI](https://img.shields.io/pypi/v/starlette_babel)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/alex-oleshkevich/starlette_babel/Lint)
![GitHub](https://img.shields.io/github/license/alex-oleshkevich/starlette_babel)
![Libraries.io dependency status for latest release](https://img.shields.io/librariesio/release/pypi/starlette_babel)
![PyPI - Downloads](https://img.shields.io/pypi/dm/starlette_babel)
![GitHub Release Date](https://img.shields.io/github/release-date/alex-oleshkevich/starlette_babel)

## Installation

Install `starlette_babel` using PIP or poetry:

```bash
pip install starlette_babel
# or
poetry add starlette_babel
```

## Features

- Locale middleware
- Multi-domain translations
- Locale selectors
- Timezone middleware
- Timezone selectors
- Locale-aware formatters
- Jinja2 integration

## Quick start

See example application in [examples/](examples/) directory of this repository.

## Setting up translator and locale features

### Configure Starlette application

To start using locale aware formatters, text translation and other components you have to set up a translator
and add middleware to your Starlette application.

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_babel import get_translator, LocaleMiddleware

supported_locales = ['be', 'en', 'pl']
shared_translator = get_translator()  # process global instance
shared_translator.load_from_directories(['/path/to/locales/'])  # one or multiple locale directories

app = Starlette(
    middleware=[
        Middleware(LocaleMiddleware, locales=supported_locales, default_locale='en'),
    ]
)
```

### Getting locale information

#### From request object

The `LocaleMiddleware` adds two state options to the request: `locale` and `language`.

```python
from babel import Locale


def index_view(request):
    current_locale: Locale = request.state.locale
    current_language: str = request.state.language
```

#### Using `get_locale` helper

Alternatively, use `get_locale` to get the locale information

```python
from babel import Locale
from starlette_babel import get_locale

locale: Locale = get_locale()
```

### Locale selectors

`LocaleMiddleware` uses locale selectors to detect the locale from the request object.
The selector is a callable that accepts `HTTPConnection` object and returns either a locale code as a string or
None. The first locale selector that returns non-None value wins.
If all selectors fail then the middleware sets locale from `default_locale` option.
The detected locale should be in the list defined by the `locales` option otherwise it won't be accepted.

The default selector order is:

1. from `locale` query parameter
2. from `language` cookie
3. from `get_preferred_language` user method (will use `request.user`, if available)
4. from `accept-language` header
5. fallback to configured default locale

#### Customizing locale selectors or changing their order

If you want to customize the way the middleware detects the locale, pass `selectors` option to the middleware:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_babel import LocaleFromHeader, LocaleFromQuery, LocaleMiddleware

app = Starlette(
    middleware=[
        Middleware(LocaleMiddleware, selectors=[
            LocaleFromQuery(), LocaleFromHeader(),
        ])
    ]
)
```

In this example we use only two selectors. They will be called in the order they are defined.

#### Custom locale selectors

You can define your own selector by writing a function or a callable object:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection

from starlette_babel import LocaleMiddleware


def my_locale_selector(conn: HTTPConnection) -> str | None:
    return 'be_BY'


app = Starlette(
    middleware=[
        Middleware(LocaleMiddleware, selectors=[
            my_locale_selector,
        ])
    ]
)
```

### Mark translatable strings

At this point your application is translatable and each request contain locale information that you can use.
Let's define some translatable strings

> Please note, that we did not write any translations and the example below won't actually translate anything.
> This is an example of how to mark strings for translation. We will cover message extraction a bit later.

```python
from starlette.responses import PlainTextResponse

from starlette_babel import gettext_lazy as _

welcome_message = _('Welcome')


def index_view(request):
    return PlainTextResponse(welcome_message)
```

### Extract translatable strings from the source code

Strings marked as translatable won't translate themselves. They should be extracted into `.po` files and compiled into
machine-readable `.mo` files. This topic is out of the scope if this documentation and is well-documented by the
[official Babel documentation](https://babel.pocoo.org/en/latest/).

A brief hint on what to do is:

1. configure `pybabel` tool via `pybabel.ini`
2. create directories for each supported locale
3. extract strings from the source code using `pybabel extract` command
4. update locale specific message catalogues (`messages.po`) using `pybabel update` command
5. compile these catalogues into machine-readable format (`messages.mo`) using `pybabel compile` command.

These commands are documented
at [https://babel.pocoo.org/en/latest/cmdline.html](https://babel.pocoo.org/en/latest/cmdline.html)

#### Locales directory structure

The locales directory is a directory where we keep our translation files. Usually, this directory called `locales`.
The structure is like this: `locales/_code_/LC_MESSAGES/messages.po` where `_code_` is a locale code.

Example:

```shell
your_app_package_name/
    locales/
      en/
        LC_MESSAGES/
          messages.po
      de/
        LC_MESSAGES/
          messages.po
      messages.pot
```

If the directory format does not match the expectation, translator would not be able to load messages and will fail
silently. You can use the [examples/locales](examples/locales) for a reference.

### Enable Jinja2 plugin

If you use Jinja2 templates you can integrate translator and formatters provided by this library with Jinja.

```python
import jinja2

from starlette_babel.contrib.jinja import configure_jinja_env

jinja_env = jinja2.Environment()
configure_jinja_env(jinja_env)
```

The `configure_jinja_env` makes the following utilities available in the templates:

#### Global functions

- `_` - alias for `gettext`
- `_p` - alias for `ngettext`

```html

<time>{{ _('Welcome') }}</time>
```

#### Filters

- datetime
- date
- time
- timedelta
- number
- currency
- percent
- scientific

All these filters are locale-aware and will format passed data using locale defined format.

```html

<time>your local time is {{ now|datetime }}</time>
```

### Manually setting the locale

You can set the current locale manually

```python
from starlette_babel import set_locale

set_locale('pl')
```

### Temporary setting the locale

You can switch locale temporary for a code block using `switch_locale` context manager. When the manager exits the
previous locale gets restored. This utility is very useful in unit tests.

```python
from starlette_babel import switch_locale, set_locale

set_locale('pl')
# all speak Polish here

with switch_locale('be'):
    # all speak Belarussian here
    ...

# all speak Polish here again
```

### Manually translating strings

You can translate messages using `translator.gettext` and `translator.ngettext` directly in the code of the view
function:

```python
from starlette_babel import Translator

translator = Translator(['/path/to/locales'])


def index_view(request):
    translated = translator.gettext('Hello', locale='en')
```

### Translation domains

> This is advanced topic. Most apps don't need this but library developers may need it.

A translation domain is like a namespace. Same message can have different translations depending on the context (aka
domain). This library natively supports domains. We infer domain name from the .po file name, dropping the extension.
For the file like `locales/en/LC_MESSAGES/errors.po` the domain is `errors`.
The default translation domain is `messages`.

```python
from starlette_babel import Translator

translator = Translator(['/path/to/locales'])
hello_message = translator.gettext('Hello', locale='en')  # uses default `messages` domain
shopping_hello_message = translator.gettext('Hello', locale='en', domain='shopping')  # uses `shopping` domain
```

#### Directory structure

The structure is exactly the same as stated above.

```shell
your_app_package_name/
    locales/
      en/
        LC_MESSAGES/
          messages.po
          shopping.po # <-- new file. defines "shopping" domain
```

## Formatters

The library integrates formatting utilities from the Babel package.
Our version automatically applies current locale/timezone without defining them manually.

Here is the list of adapted formatters:

- format_datetime
- format_date
- format_time
- format_timedelta
- format_interval
- format_number
- format_currency
- format_percent
- format_scientific

Consult [Babel documentation](https://babel.pocoo.org/en/latest/index.html) for more information.

### Usage

```python
import datetime

from starlette_babel import format_datetime, set_locale, set_timezone

set_locale('be')
set_timezone('Europe/Minsk')
now = datetime.datetime.now()
local_time = format_datetime(now)  # <-- this
```

### Jinja integration

There formatters are automatically exposed to templates after applying `configure_jinja_env` on Jinja environment.

## Timezone support

To enable timezone support add `TimezoneMiddleware`. The middleware behaves much like `LocaleMiddleware` and shares same
concepts.

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_babel import TimezoneMiddleware

app = Starlette(
    middleware=[
        Middleware(TimezoneMiddleware, fallback='Europe/London')
    ]
)
```

By default, the middleware will try these selectors:

1. from `tz` query parameter
2. from `timezone` cookie
2. from `get_timezone` user method

### Retrieving timezone information

#### Reading timezone from request object

```python
from pytz import BaseTzInfo


def index_view(request):
    timezone: BaseTzInfo = request.state.timezone
```

#### Using `get_timezone` helper

Use `get_timezone` helper to get the timezone information set by the middleware.
If middleware not used it will return UTC zone info.

```python
from pytz import BaseTzInfo

from starlette_babel import get_timezone

tz: BaseTzInfo = get_timezone()
```

### Customizing selectors or changing their order

You can change selectors set or the order they are defined by configuring `selectors` option of the middleware:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_babel import TimezoneFromCookie, TimezoneFromQuery, TimezoneMiddleware

app = Starlette(
    middleware=[
        Middleware(TimezoneMiddleware, fallback='Europe/London', selectors=[
            TimezoneFromQuery(), TimezoneFromCookie(),
        ])
    ]
)
```

### Custom timezone selectors

A selector is a callable that accepts `HTTPConnection` and returns timezone code as a string:

```python
from starlette.applications import Starlette
from starlette.middleware import Middleware

from starlette_babel import TimezoneMiddleware


def my_timezone_selector(conn):
    return 'Europe/Minsk'


app = Starlette(
    middleware=[
        Middleware(TimezoneMiddleware, fallback='Europe/London', selectors=[
            my_timezone_selector,
        ])
    ]
)
```

### Setting timezone manually

Use `set_timezone` to set the timezone.

```python
from starlette_babel import set_timezone

set_timezone('Europe/Minsk')
```

### Temporary switch timezone

Use `set_timezone` to set the timezone.

```python
from starlette_babel import switch_timezone

set_timezone('Europe/Minsk')
# time in +03

with switch_timezone('Europe/Warsaw'):
    # time in +02
    ...

# time in +03 again
```

### Convert datetime into user local time

You can apply currently active timezone to any datetime instance using `to_user_timezone` helper.

```python
import datetime
from starlette_babel import to_user_timezone, set_timezone

set_timezone('Europe/Minsk')
now = datetime.datetime.utcnow()  # time in UTC
user_now = to_user_timezone(now)  # time in Europe/Minsk
```

### Convert user local time to UTC

You can also convert datetime instance back to UTC using `to_utc` helper.

```python
import datetime

from starlette_babel import set_timezone, to_user_timezone, to_utc

set_timezone('Europe/Minsk')
now = datetime.datetime.now()  # time in UTC
user_now = to_user_timezone(now)  # time in Europe/Minsk
utc_now = to_utc(user_now)  # time in UTC again
```

### Getting current time in user timezone

To get current user time use `now` helper.

```python
from starlette_babel import set_timezone, now

set_timezone('Europe/Minsk')
user_now = now()  # time in Europe/Minsk
```
