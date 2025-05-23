import yaml
from typing import Dict, Any


def parse_alertmanager_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config
