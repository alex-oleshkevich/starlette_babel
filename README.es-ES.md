

# Starlette Babel

Proporciona traducciones, formateadores y soporte de zona horaria para aplicaciones de Starlette mediante la integración de la biblioteca Babel.

![PyPI](https://img.shields.io/pypi/v/starlette_babel)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/alex-oleshkevich/starlette_babel/lint_and_test.yml?branch=master)
![GitHub](https://img.shields.io/github/license/alex-oleshkevich/starlette_babel)
![Libraries.io dependency status for latest release](https://img.shields.io/librariesio/release/pypi/starlette_babel)
![PyPI - Downloads](https://img.shields.io/pypi/dm/starlette_babel)
![GitHub Release Date](https://img.shields.io/github/release-date/alex-oleshkevich/starlette_babel)

## Instalación

Instale `starlette_babel` usando pip o uv:

```bash
pip install starlette_babel
# or
uv add starlette_babel
```

## Características

- Middleware de localidad
- Traducciones multidominio
- Traducciones contextuales mediante `pgettext` / `npgettext`
- Selectores de localidad
- Middleware de zona horaria
- Selectores de zona horaria
- Formateadores sensibles a la localidad (fechas, horas, números, monedas, porcentajes, unidades, listas)
- Negociación de localidad mediante `negotiate_locale`
- Análisis de números y fechas mediante `parse_number` / `parse_decimal` / `parse_date` / `parse_time`
- Detección de dirección del texto (LTR/RTL) mediante `get_text_direction`
- Integración con Jinja2

## Inicio rápido

Consulte la aplicación de ejemplo en el directorio [examples/](examples/) de este repositorio.

## Configuración del traductor y las funcionalidades de localidad

### Configurar la aplicación Starlette

Para comenzar a utilizar formateadores sensibles a la localidad, traducción de texto y otros componentes, debe configurar un traductor y agregar middleware a su aplicación Starlette.

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

### Obtener información de localidad

#### Desde el objeto de solicitud

El `LocaleMiddleware` añade tres opciones de estado a la solicitud: `locale`, `language` y `text_direction`.

```python
from babel import Locale


def index_view(request):
    current_locale: Locale = request.state.locale
    current_language: str = request.state.language
    current_direction: str = request.state.text_direction  # 'ltr' or 'rtl'
```

#### Usando el auxiliar `get_locale`

Alternativamente, use `get_locale` para obtener la información de localidad

```python
from babel import Locale
from starlette_babel import get_locale

locale: Locale = get_locale()
```

### Selectores de localidad

`LocaleMiddleware` utiliza selectores de localidad para detectar la localidad desde el objeto de solicitud.
El selector es una función invocable que acepta un objeto `HTTPConnection` y devuelve un código de localidad como cadena o None. El primer selector que devuelva un valor distinto de None es el que se utiliza.
Si todos los selectores fallan, el middleware establece la localidad desde la opción `default_locale`.
La localidad detectada debe estar en la lista definida por la opción `locales`, de lo contrario no será aceptada.

El orden predeterminado de los selectores es:

1. desde el parámetro de consulta `locale`
2. desde la cookie `language`
3. desde el método de usuario `get_preferred_language` (usará `request.user`, si está disponible)
4. desde el encabezado `accept-language`
5. uso de la localidad predeterminada configurada como respaldo

#### Personalizar selectores de localidad o cambiar su orden

Si desea personalizar la forma en que el middleware detecta la localidad, pase la opción `selectors` al middleware:

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

En este ejemplo solo usamos dos selectores. Se llamarán en el orden en que se definen.

#### Selectores de localidad personalizados

Puede definir su propio selector escribiendo una función o un objeto invocable:

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

### Marcar cadenas traducibles

En este punto, su aplicación es traducible y cada solicitud contiene información de localidad que puede utilizar.
Definamos algunas cadenas traducibles

> Tenga en cuenta que no hemos escrito ninguna traducción y el ejemplo a continuación no traducirá nada realmente.
> Este es un ejemplo de cómo marcar cadenas para su traducción. Cubriremos la extracción de mensajes un poco más adelante.

```python
from starlette.responses import PlainTextResponse

from starlette_babel import gettext_lazy as _

welcome_message = _('Welcome')


def index_view(request):
    return PlainTextResponse(welcome_message)
```

### Extraer cadenas traducibles del código fuente

Las cadenas marcadas como traducibles no se traducen por sí solas. Deben extraerse en archivos `.po` y compilarse en archivos `.mo` legibles por máquina. Este tema está fuera del alcance de esta documentación y está bien documentado en la [documentación oficial de Babel](https://babel.pocoo.org/en/latest/).

Una breve indicación sobre qué hacer es:

1. configurar la herramienta `pybabel` mediante `pybabel.ini`
2. crear directorios para cada localidad admitida
3. extraer cadenas del código fuente usando el comando `pybabel extract`
4. actualizar los catálogos de mensajes específicos de la localidad (`messages.po`) usando el comando `pybabel update`
5. compilar estos catálogos en formato legible por máquina (`messages.mo`) usando el comando `pybabel compile`.

Estos comandos están documentados
en [https://babel.pocoo.org/en/latest/cmdline.html](https://babel.pocoo.org/en/latest/cmdline.html)

#### Estructura del directorio de localidades

El directorio locales es donde almacenamos nuestros archivos de traducción. Por lo general, este directorio se llama `locales`.
La estructura es la siguiente: `locales/_code_/LC_MESSAGES/messages.po` donde `_code_` es un código de localidad.

Ejemplo:

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

Si el formato del directorio no coincide con lo esperado, el traductor no podrá cargar los mensajes y fallará silenciosamente. Puede usar [examples/locales](examples/locales) como referencia.

### Habilitar el plugin de Jinja2

Si utiliza plantillas Jinja2, puede integrar el traductor y los formateadores proporcionados por esta biblioteca con Jinja.

```python
import jinja2

from starlette_babel.contrib.jinja import configure_jinja_env

jinja_env = jinja2.Environment()
configure_jinja_env(jinja_env)
```

El `configure_jinja_env` hace disponibles las siguientes utilidades en las plantillas:

#### Funciones globales

- `_` - alias de `gettext`
- `_p` - alias de `ngettext`
- `_c` - alias de `pgettext` (contextual)
- `_cp` - alias de `npgettext` (plural contextual)
- `locale` - objeto `Locale` actual
- `language` - código de idioma actual
- `text_direction` - `ltr` o `rtl` para la localidad actual
- `month_names`, `day_names` - nombres del calendario localizados
- `currency_symbol`, `currency_name` - etiquetas de moneda localizadas

```html
<html dir="{{ text_direction() }}" lang="{{ language() }}">
    <time>{{ _('Welcome') }}</time>
    <span>{{ _c('month', 'May') }}</span>
</html>
```

La etiqueta `{% trans %}` acepta un contexto como su primer argumento:

```html
{% trans "verb" %}May{% endtrans %}
```

#### Filtros

- datetime
- date
- time
- timedelta
- interval
- skeleton
- number
- decimal
- compact_decimal
- currency
- compact_currency
- percent
- scientific
- unit
- format_list

Todos estos filtros son sensibles a la localidad y formatearán los datos proporcionados utilizando el formato definido por la localidad.

> El formateador de listas se expone como `format_list` en lugar de `list`, porque Jinja ya incluye un filtro incorporado `list` que no debemos enmascarar.

```html
<time>your local time is {{ now|datetime }}</time>
```

### Establecer la localidad manualmente

Puede establecer la localidad actual manualmente

```python
from starlette_babel import set_locale

set_locale('pl')
```

### Establecer la localidad temporalmente

Puede cambiar la localidad temporalmente para un bloque de código usando el administrador de contexto `switch_locale`. Cuando el administrador se cierra, se restaura la localidad anterior. Esta utilidad es muy útil en pruebas unitarias.

```python
from starlette_babel import switch_locale, set_locale

set_locale('pl')
# all speak Polish here

with switch_locale('be'):
    # all speak Belarussian here
    ...

# all speak Polish here again
```

### Traducir cadenas manualmente

Puede traducir mensajes usando `translator.gettext` y `translator.ngettext` directamente en el código de la función de vista:

```python
from starlette_babel import Translator

translator = Translator(['/path/to/locales'])


def index_view(request):
    translated = translator.gettext('Hello', locale='en')
```

### Dominios de traducción

> Este es un tema avanzado. La mayoría de las aplicaciones no lo necesitan, pero los desarrolladores de bibliotecas pueden necesitarlo.

Un dominio de traducción es similar a un espacio de nombres. El mismo mensaje puede tener diferentes traducciones dependiendo del contexto (también conocido como dominio). Esta biblioteca admite dominios nativamente. Inferimos el nombre del dominio desde el nombre del archivo .po, omitiendo la extensión. Para un archivo como `locales/en/LC_MESSAGES/errors.po` el dominio es `errors`.
El dominio de traducción predeterminado es `messages`.

```python
from starlette_babel import Translator

translator = Translator(['/path/to/locales'])
hello_message = translator.gettext('Hello', locale='en')  # uses default `messages` domain
shopping_hello_message = translator.gettext('Hello', locale='en', domain='shopping')  # uses `shopping` domain
```

#### Estructura de directorios

La estructura es exactamente la misma que se indicó anteriormente.

```shell
your_app_package_name/
    locales/
      en/
        LC_MESSAGES/
          messages.po
          shopping.po # <-- new file. defines "shopping" domain
```

## Formateadores

La biblioteca integra utilidades de formateo del paquete Babel.
Nuestra versión aplica automáticamente la localidad/zona horaria actual sin definirlas manualmente.

Aquí está la lista de formateadores adaptados:

Fechas y horas:

- format_datetime
- format_date
- format_time
- format_timedelta
- format_interval
- format_skeleton
- parse_date
- parse_time
- get_month_names
- get_day_names

Números, monedas y unidades:

- format_number (alias de `format_decimal`)
- format_decimal
- format_compact_decimal
- format_currency
- format_compact_currency
- format_percent
- format_scientific
- format_unit
- parse_decimal
- parse_number
- get_currency_symbol
- get_currency_name

Listas:

- format_list

Consulte la [documentación de Babel](https://babel.pocoo.org/en/latest/index.html) para obtener más información.

> Babel no proporciona una contraparte `parse_datetime` para `parse_date` / `parse_time`, por lo que nosotros tampoco.

### Dirección del texto

Use `get_text_direction` para renderizar correctamente los idiomas de derecha a izquierda. Sin un argumento, utiliza la localidad actual.

```python
from starlette_babel import get_text_direction

get_text_direction()      # 'ltr' or 'rtl' for the current locale
get_text_direction('ar')  # 'rtl'
```

`LocaleMiddleware` también lo expone en el estado de la solicitud:

```python
def index_view(request):
    direction: str = request.state.text_direction
```

### Uso

```python
import datetime

from starlette_babel import format_datetime, set_locale, set_timezone

set_locale('be')
set_timezone('Europe/Minsk')
now = datetime.datetime.now()
local_time = format_datetime(now)  # <-- this
```

### Integración con Jinja

Estos formateadores se exponen automáticamente a las plantillas después de aplicar `configure_jinja_env` en el entorno de Jinja.

## Soporte de zona horaria

Para habilitar el soporte de zona horaria, agregue `TimezoneMiddleware`. El middleware se comporta de manera similar a `LocaleMiddleware` y comparte los mismos conceptos.

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

Por defecto, el middleware intentará estos selectores:

1. desde el parámetro de consulta `tz`
2. desde la cookie `timezone`
3. desde el método de usuario `get_timezone`

### Obtener información de zona horaria

#### Leer zona horaria desde el objeto de solicitud

```python
import datetime


def index_view(request):
    timezone: datetime.tzinfo = request.state.timezone
```

#### Usando el auxiliar `get_timezone`

Use el auxiliar `get_timezone` para obtener la información de zona horaria establecida por el middleware.
Si no se usa el middleware, devolverá UTC.

```python
import datetime

from starlette_babel import get_timezone

tz: datetime.tzinfo = get_timezone()
```

### Personalizar selectores o cambiar su orden

Puede cambiar el conjunto de selectores o el orden en que se definen configurando la opción `selectors` del middleware:

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

### Selectores de zona horaria personalizados

Un selector es una función invocable que acepta `HTTPConnection` y devuelve el código de zona horaria como una cadena:

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

### Establecer zona horaria manualmente

Use `set_timezone` para establecer la zona horaria.

```python
from starlette_babel import set_timezone

set_timezone('Europe/Minsk')
```

### Cambiar zona horaria temporalmente

Use `switch_timezone` para cambiar la zona horaria.

```python
from starlette_babel import switch_timezone

set_timezone('Europe/Minsk')
# time in +03

with switch_timezone('Europe/Warsaw'):
    # time in +02
    ...

# time in +03 again
```

### Convertir datetime a hora local del usuario

Puede aplicar la zona horaria activa actualmente a cualquier instancia de datetime usando el auxiliar `to_user_timezone`.

```python
import datetime
from starlette_babel import to_user_timezone, set_timezone

set_timezone('Europe/Minsk')
now = datetime.datetime.now(datetime.timezone.utc)  # time in UTC
user_now = to_user_timezone(now)  # time in Europe/Minsk
```

### Convertir hora local del usuario a UTC

También puede convertir la instancia de datetime de vuelta a UTC usando el auxiliar `to_utc`.

```python
import datetime

from starlette_babel import set_timezone, to_user_timezone, to_utc

set_timezone('Europe/Minsk')
now = datetime.datetime.now()  # time in UTC
user_now = to_user_timezone(now)  # time in Europe/Minsk
utc_now = to_utc(user_now)  # time in UTC again
```

### Obtener la hora actual en la zona horaria del usuario

Para obtener la hora actual del usuario, use el auxiliar `now`.

```python
from starlette_babel import set_timezone, now

set_timezone('Europe/Minsk')
user_now = now()  # time in Europe/Minsk
```
