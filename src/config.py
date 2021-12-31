import yaml
import os

if not os.path.exists('../tmp'):
    os.makedirs('../tmp')

with open('../config.yml') as f:
    configMap = yaml.safe_load(f)


def getAttribute(field, default='INVALIDKEY'):
    return configMap.get(field, default)
