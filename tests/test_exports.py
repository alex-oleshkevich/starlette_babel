"""Guard against public API drift.

Functions have been added to the submodules before without ever being re-exported
from the package root, making them unreachable via `from starlette_babel import ...`.
"""

import inspect
import pytest
import types

import starlette_babel
from starlette_babel import formatters, locale, timezone, translator

MODULES = [formatters, locale, timezone, translator]

# Names that intentionally stay module-private and are not part of the package API.
NOT_EXPORTED = {
    "parse_locale",  # internal helper, documented as such
    "gettext",  # module-level name shadowed by the Translator method in some call sites
}


def public_names(module: types.ModuleType) -> list[str]:
    """Public callables and type aliases defined in the module itself, not imported into it."""
    names = []
    for name, value in vars(module).items():
        if name.startswith("_"):
            continue
        if not (inspect.isfunction(value) or inspect.isclass(value)):
            continue
        if getattr(value, "__module__", None) != module.__name__:
            continue
        names.append(name)
    return names


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__)
def test_public_names_are_exported(module: types.ModuleType) -> None:
    missing = [
        name for name in public_names(module) if name not in starlette_babel.__all__ and name not in NOT_EXPORTED
    ]
    assert not missing, f"{module.__name__} defines public names missing from starlette_babel.__all__: {missing}"


def test_all_entries_are_importable() -> None:
    """Every name in __all__ actually resolves on the package."""
    missing = [name for name in starlette_babel.__all__ if not hasattr(starlette_babel, name)]
    assert not missing, f"__all__ lists names that do not exist: {missing}"


def test_all_has_no_duplicates() -> None:
    duplicates = {name for name in starlette_babel.__all__ if starlette_babel.__all__.count(name) > 1}
    assert not duplicates, f"__all__ contains duplicates: {duplicates}"
