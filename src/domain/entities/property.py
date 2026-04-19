from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Property:
    id: int
    title: str
    city: str
    price: int
    layout: str
    walk_min: int
    pet: bool
