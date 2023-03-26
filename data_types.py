from dataclasses import dataclass, field
from typing import Callable, Set


@dataclass
class Developer:
    name: str
    reviewer_number: int
    preferable_reviewer_names: Set[str]
    reviewer_names: Set[str] = field(default_factory=set)
    review_for: Set[str] = field(default_factory=set)
    order: int = field(default=1)


@dataclass
class SelectableConfigure:
    names: Set[str]
    number_getter: Callable[[], int]
