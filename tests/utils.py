"""Test utilities for mutating developer data in tests."""

from typing import Any, Dict, List

from lib.data_types import Developer


def mutate_devs(
    devs: List[Developer],
    attribute_name: str,
    dev_attribute_value_mapper: Dict[str, Any],
) -> None:
    """
    Mutate developer attributes for testing purposes.

    Args:
        devs: List of Developer objects to mutate
        attribute_name: Name of the attribute to set
        dev_attribute_value_mapper: Dict mapping developer names to new values
    """
    dev_keys = dev_attribute_value_mapper.keys()
    for dev in devs:
        if dev.name in dev_keys:
            setattr(dev, attribute_name, dev_attribute_value_mapper[dev.name])
