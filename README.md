# Starlette Babel

Locale, timezone, and translations support for Starlette.

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

### Create locale directories

The locale directory is a directory where translation files are kept. Usually, this directory called `locales`.
The directory structure is the following:

```shell
your_app_package_name/
    locales/
      en/
        LC_MESSAGES/
          messages.po
      messages.pot
```

If the directory format does not match the expectation, translator would not be able to load messages and will fail
silently. You can use the [examples/locales](examples/locales) for a reference.

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

### Getting locale information from Request instance

The `LocaleMiddleware` makes two state options available to you via request: `locale` and `language`.

```python
from babel import Locale


def index_view(request):
    current_locale: Locale = request.state.locale
    current_language: str = request.state.language
```

### Locale selectors

`LocaleMiddleware` uses locale selectors to detect a locale from the request object.
The locale selector is a callable that accepts `HTTPConnection` object and returns either locale code as string or
None. The first locale selector that returns non-None value wins.
If all selectors fail then middleware sets locale from `default_locale` option.
The detected locale should be in the list defined by the `locales` middleware option otherwise it won't be accepted.

The default selectors order is:

1. query params
2. cookie
3. user object (from `request.user`, if available)
4. `accept-language` header
5. default locale from the middleware argument

#### Customizing locale selectors or changing their order

If you want to customize the way the middleware detects the locale, you can pass `selectors` option to the middleware:

```python
from starlette.middleware import Middleware
from starlette.applications import Starlette
from starlette_babel import LocaleMiddleware, LocaleFromQuery, LocaleFromHeader

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

As the locale selector is a callable, you can define your own by writing a function or a callable object:

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
from starlette_babel import gettext_lazy as _
from starlette.responses import PlainTextResponse

welcome_message = _('Welcome')


def index_view(request):
    return PlainTextResponse(welcome_message)
```

### Setup pybabel

Now it is a time to collect messages from our code. For that we will use `pybabel` command line utility that comes
with `babel` package.

#### Create `pybabel.ini` configuration file

Put this code into `pybabel.ini`

```ini
[python: **.py]

; enable jinja templates support
[jinja2: **/templates/**.html]
extensions = jinja2.ext.i18n
```

#### Extract translatable strings from source code into `messages.pot`

We assume that you are in the application directory.

```shell
pybabel extract -o locales/messages.pot -F pybabel.ini ./
```

This command scans the source code and outputs found strings into `messages.pot` template file.
We will use this file later to generate or update per-locale `messages.po` files.

### Update .po files

Now we have a template file, and we can sync our locale-specific messages with the template.

```shell
pybabel update -i locales/messages.pot -d locales/
```

Now we have `messages.po` files for each locale in sync with the template file.

### Compile .po files

The final step is to compile `messages.po` into machine-readable `messages.mo` files.

```shell
pybabel compile -d locales/
```

Restart your application server. The application should speak in your language now.
