"""The validate_config module.

It has the following classes:
    - ValidateConfig: Validate the config file.

Usage:
    Used to validate the config file.
"""
from __future__ import annotations

from pathlib import Path

import pydantic
import yaml
from pydantic import Field, HttpUrl, field_validator
from pydantic.dataclasses import dataclass

IP_ADDRESS_PARTS = 4
MAX_IP_PART_VALUE = 255


@dataclass
class ValidateConfig:
    """Validate the config file.

    Attributes:
        validator_address (str): The address of the validator.
        price_feed_addr (str): The address of the oracle.
        APIs (list[HttpUrl]): The list of API links.

    """

    validator_address: str = Field(..., min_length=50, max_length=50)
    price_feed_addr: str = Field(..., min_length=43, max_length=43)
    APIs: list[HttpUrl]

    # TO DO test new pydantic validator!
    @field_validator("APIs", each_item=True)
    def validate_links(self, v: str | None) -> str:
        """Validate a single API link.

        Args:
            v (str | None): The link to validate.

        Returns:
            str: The validated link.

        Raises:
            pydantic.ValidationError: If the link is invalid.

        """
        if v is None:
            msg = "Link cannot be null"
            raise pydantic.ValidationError(msg, ValidateConfig)

        if v.startswith(("http://", "https://")):
            try:
                HttpUrl(v)
            except pydantic.ValidationError as e:
                msg = f"Invalid link format: {e}"
                raise pydantic.ValidationError(msg) from None
        elif v in ["localhost", "127.0.0.1"] or self._validate_ip_address(v):
            return v
        else:
            msg = "Invalid link format"
            raise pydantic.ValidationError(msg, ValidateConfig)
    @staticmethod
    def _validate_ip_address(ip: str) -> bool:
        """Validate an IP address.

        Args:
            ip (str): The IP address to validate.

        Returns:
            bool: True if the IP address is valid, False otherwise.

        """
        parts: list[str] = ip.split(".")
        if len(parts) != IP_ADDRESS_PARTS:
            return False

        return all(0 <= int(part) <= MAX_IP_PART_VALUE for part in parts)
# Add more validations later

def validate_yaml(file_path: str) -> ValidateConfig:
    """Validate a YAML file.

    Args:
        file_path (str): The path to the YAML file to validate.

    Returns:
        ValidateConfig: The validated YAML data.

    Raises:
        pydantic.ValidationError: If the YAML data is invalid.

    """
    with Path.open(file_path) as file:
        data = yaml.safe_load(file)
    return ValidateConfig(**data)
