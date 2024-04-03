import yaml
import os

if not os.path.exists('../tmp'):
    os.makedirs('../tmp')

with open('./config.yml', encoding='utf-8') as f:
    configMap = yaml.safe_load(f)


def get_attribute(field, default='INVALIDKEY'):
    return configMap.get(field, default)
