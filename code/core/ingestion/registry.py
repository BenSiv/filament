from __future__ import annotations

from typing import Dict, Iterable, Type

from .base import IngestionSource


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, Type[IngestionSource]] = {}

    def register(self, source_cls: Type[IngestionSource]) -> Type[IngestionSource]:
        name = source_cls.name
        if not name:
            raise ValueError("Ingestion source must define a name")
        self._sources[name] = source_cls
        return source_cls

    def get(self, name: str) -> Type[IngestionSource]:
        if name not in self._sources:
            raise KeyError(f"Unknown source '{name}'")
        return self._sources[name]

    def list(self) -> Iterable[Type[IngestionSource]]:
        return list(self._sources.values())


REGISTRY = SourceRegistry()
