import yaml

with open('../config.yml') as f:
    configMap = yaml.safe_load(f)


def getAttribute(field):
    return configMap.get(field, 'INVALIDKEY')
