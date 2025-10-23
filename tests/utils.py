from typing import Any, Dict, List

from lib.data_types import Developer


def mutate_devs(
    devs: List[Developer],
    attribute_name: str,
    dev_attribute_value_mapper: Dict[str, Any],
):
    dev_keys = dev_attribute_value_mapper.keys()
    for dev in devs:
        if dev.name in dev_keys:
            setattr(dev, attribute_name, dev_attribute_value_mapper[dev.name])
