import yaml
import yaml_include


yaml.add_constructor("!import", yaml_include.Constructor(base_dir='config'))

def get_config():
    return get_config_from_yaml()


def get_config_from_yaml() -> dict:
    with open('config/settings.yaml', 'r', encoding='utf-8') as f:
        settings: dict = yaml.full_load(f)
    return settings.get('settings', {})
