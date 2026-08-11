"""
Library integration boundary.

Publisher does not import the Library repo's package (the two repos have no shared dependency,
per 07_DISPATCH_REPO_PLACEMENT_PLAN.md — each repo is independently built). Instead, Publisher
depends on this small duck-typed interface, which matches the `library.current()` /
`library.resolve_packet()` service surfaces defined in DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md
Section 6. A real integration points a `LibraryClient`-shaped adapter at a running Library
service (e.g. `dispatch_library.service.LibraryService`, whose method signatures this interface
mirrors exactly); this repo ships an in-process stub for local/offline testing.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

MISSING = "MISSING"


class LibraryClient(Protocol):
    def current(self, object_code: str) -> Optional[Any]:
        ...

    def resolve_packet(self, recipe_type: str) -> Dict[str, Any]:
        ...

    def get_recipe(self, recipe_type: str) -> Optional[Dict[str, Any]]:
        ...


class StubLibraryClient:
    """In-process reference LibraryClient for local/offline Publisher testing.

    Holds a flat object_code -> object mapping and a recipe_type -> recipe-metadata mapping,
    supplied directly by the caller (e.g. by a test, or by wiring in real Library objects).
    Never invents a resolution for an object_code it was not given — always returns MISSING.
    """

    def __init__(
        self,
        objects: Optional[Dict[str, Any]] = None,
        recipes: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self._objects: Dict[str, Any] = dict(objects or {})
        self._recipes: Dict[str, Dict[str, Any]] = dict(recipes or {})

    def put_object(self, object_code: str, obj: Any) -> None:
        self._objects[object_code] = obj

    def put_recipe(self, recipe_type: str, recipe: Dict[str, Any]) -> None:
        self._recipes[recipe_type] = recipe

    def current(self, object_code: str) -> Optional[Any]:
        return self._objects.get(object_code)

    def get_recipe(self, recipe_type: str) -> Optional[Dict[str, Any]]:
        return self._recipes.get(recipe_type)

    def resolve_packet(self, recipe_type: str) -> Dict[str, Any]:
        recipe = self.get_recipe(recipe_type)
        if recipe is None:
            return {}
        resolved: Dict[str, Any] = {}
        for object_code in recipe.get("required_library_object_codes", []):
            resolved[object_code] = self._objects.get(object_code, MISSING)
        return resolved
