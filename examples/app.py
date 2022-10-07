import math
import os.path
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from starlette_babel import LocaleMiddleware, TimezoneMiddleware, timezone
from starlette_babel.contrib.jinja import configure_jinja_env

this_dir = os.path.dirname(__file__)
templates = Jinja2Templates(os.path.join(this_dir, "templates"))
configure_jinja_env(templates.env)


def index_view(request: Request) -> Response:
    midnight = timezone.now().replace(hour=0, minute=0, second=0)
    current_time = timezone.now()
    since_midnight = current_time - midnight
    million = 1_000_000
    price = 2_500
    percent = 97 / 100
    pi_number = math.pi
    currency_map = {
        "pl": "PLN",
        "be": "BYN",
        "en": "USD",
    }
    currency = currency_map.get(request.state.locale.language, "UNK")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_time": current_time,
            "since_midnight": since_midnight,
            "million": million,
            "price": price,
            "currency": currency,
            "percent": percent,
            "pi_number": pi_number,
        },
    )


def select_language_view(request: Request) -> Response:
    response = RedirectResponse("/")
    response.set_cookie("language", request.query_params.get("lang", ""))
    return response


def select_timezone_view(request: Request) -> Response:
    response = RedirectResponse("/")
    response.set_cookie("timezone", request.query_params.get("tz", ""))
    return response


app = Starlette(
    debug=True,
    routes=[
        Route("/", index_view),
        Route("/set-lang", select_language_view),
        Route("/set-tz", select_timezone_view),
    ],
    middleware=[
        Middleware(LocaleMiddleware, languages=["en", "be", "pl"], default_locale="pl"),
        Middleware(TimezoneMiddleware, fallback="UTC"),
    ],
)
