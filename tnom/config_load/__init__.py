"""The config_load package.

The config_load package provides functions to load the config and alert YAML files.
"""
from .load_yml import load_alert_yml, load_config_yml

__all__ = ["load_alert_yml", "load_config_yml"]
