def mutate_devs(devs, attribute_name, dev_attribute_value_mapper):
    dev_keys = dev_attribute_value_mapper.keys()
    for dev in devs:
        if dev.name in dev_keys:
            setattr(dev, attribute_name, dev_attribute_value_mapper[dev.name])
