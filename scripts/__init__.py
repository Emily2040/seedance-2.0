"""Package bootstrap for validators that also run as standalone scripts.

The validators use package-relative imports when loaded as ``scripts.*`` and
top-level imports when executed directly.  If the sibling loader was already
imported through the other spelling, reuse that exact module object so callers
see one ``StrictJSONError`` class.  Never replace an unrelated module that
happens to own the generic top-level name ``strict_json``.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _same_loader(module: object) -> bool:
    origin = getattr(module, "__file__", None)
    if not isinstance(origin, str):
        return False
    sibling = Path(__file__).with_name("strict_json.py")
    try:
        return Path(origin).resolve() == sibling.resolve()
    except (OSError, RuntimeError):
        left = origin.replace("\\", "/").casefold()
        right = str(sibling).replace("\\", "/").casefold()
        return left == right


_top_level = sys.modules.get("strict_json")
if _top_level is not None and _same_loader(_top_level):
    # Import machinery honors a pre-populated fully-qualified name.  Reusing
    # the sibling's earlier top-level import avoids a second exception class.
    sys.modules.setdefault(f"{__name__}.strict_json", _top_level)
    _strict_json = _top_level
else:
    from . import strict_json as _strict_json

    # This is an alias only when the generic name is free.  ``setdefault`` is
    # deliberate: package import must never clobber an unrelated dependency.
    sys.modules.setdefault("strict_json", _strict_json)
