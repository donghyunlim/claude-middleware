import os, yaml


def load_config():
    env = os.environ.get("APP_ENV", "development")
    with open(os.path.join(os.path.dirname(__file__), "default.yaml")) as f:
        cfg = yaml.safe_load(f)
    override = os.path.join(os.path.dirname(__file__), f"{env}.yaml")
    if os.path.exists(override):
        with open(override) as f:
            for section, values in (yaml.safe_load(f) or {}).items():
                cfg.setdefault(section, {}).update(values)
    return cfg
