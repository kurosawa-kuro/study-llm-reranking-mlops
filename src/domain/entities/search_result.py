from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.entities.property import Property


@dataclass
class SearchResult:
    count: int
    items: list[Property] = field(default_factory=list)
