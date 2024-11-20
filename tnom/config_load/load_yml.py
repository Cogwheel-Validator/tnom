"""Load YAML config files.

There are two functions:
    - load_config_yml: Loads and checks the config YAML file for errors.
    - load_alert_yml: Loads and checks the alert YAML file for errors.

Usage:
    Used to load the config and alert YAML files.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


def load_alert_yml(yml_file: Path) -> dict[str, Any]:
    """Loads and checks the alert YAML file for errors.

    Args:
        yml_file (Path): The path to the YAML file.

    Returns:
        dict[str, Any]: The loaded YAML data.

    Raises:
        ValueError: If the YAML file doesn't contain at least one alert trigger.
        ValueError: If the YAML file is missing a required field.

    """
    with yml_file.open() as f:
        data = yaml.safe_load(f)

    # Check for the presence of at least one alert trigger
    if not any("telegram_alert" in data, "pagerduty_alert" in data):
        msg = "There needs to be at least one alert trigger"
        raise ValueError(msg)

    # Check for the presence of required fields
    required_fields : dict[str, list[str]] = {
        "telegram_alert": ["telegram_bot_token", "chat_id"],
        "pagerduty_alert": ["pagerduty_routing_key"],
    }

    for trigger, fields in required_fields.items():
        if data.get(trigger) is True:
            for field in fields:
                if field not in data:
                    msg = f"{field} must be provided for {trigger}"
                    raise ValueError(msg)

    return data

def load_config_yml(yml_file: Path) -> dict[str, Any]:
    """Loads and checks the config YAML file for errors.

    Args:
        yml_file (Path): The path to the YAML file.

    Returns:
        dict[str, Any]: The loaded YAML data.

    Raises:
        ValueError: If the YAML file is missing a required field.

    """
    with yml_file.open() as f:
        data = yaml.safe_load(f)

    required_fields = ["validator_address", "APIs", "price_feed_addr"]
    for field in required_fields:
        if field not in data:
            msg = f"{field} must be provided"
            raise ValueError(msg)

    return data
