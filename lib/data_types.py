"""Data type definitions for the code review rotation system."""

from dataclasses import dataclass, field
from typing import Callable, Set


@dataclass
class Developer:
    """
    Represents a developer or team in the rotation system.

    Attributes:
        name: Developer or team name
        reviewer_number: Number of reviewers to assign
        preferable_reviewer_names: Set of preferred reviewer names
        reviewer_names: Assigned reviewer names (populated by allocation)
        reviewer_indexes: Set of assigned reviewer indexes (legacy)
        review_for: Set of developer names this person is reviewing (tracking)
        order: Order for processing (used in some allocation logic)
    """

    name: str
    reviewer_number: int
    preferable_reviewer_names: Set[str] = field(default_factory=set)
    reviewer_names: Set[str] = field(default_factory=set)
    reviewer_indexes: Set[str] = field(default_factory=set)
    review_for: Set[str] = field(default_factory=set)
    order: int = field(default=0)


@dataclass
class SelectableConfigure:
    """
    Configuration for selecting reviewers in allocation phase.

    Attributes:
        names: Set of available reviewer names to select from
        number_getter: Callable that returns how many reviewers to select
    """

    names: Set[str]
    number_getter: Callable[[], int]
