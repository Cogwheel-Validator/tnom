"""The validate_config module.

It has the following classes:
    - ValidateConfig: Validate the config file.
Usage:
    - Used to validate the config file.
"""

from __future__ import annotations

from pathlib import Path

import pydantic
import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator

IP_ADDRESS_PARTS = 4
MAX_IP_PART_VALUE = 255

class ValidateConfig(BaseModel):
    """Validate the config file.

    Attributes:
        validator_address (str): The address of the validator.
        price_feed_addr (str): The address of the oracle.
        APIs (list[HttpUrl]): The list of API links.

    """

    validator_address: str = Field(..., min_length=50, max_length=50)
    price_feed_addr: str = Field(..., min_length=43, max_length=43)
    APIs: list[HttpUrl]

    @field_validator("APIs", mode="before")
    @classmethod
    def validate_links(cls, value: list[str | HttpUrl]) -> list[HttpUrl]:
        """Validate API links.

        Args:
            value (list[Union[str, HttpUrl]]): List of links to validate.

        Returns:
            list[HttpUrl]: List of validated links.

        Raises:
            ValueError: If any link is invalid.

        """
        validated_urls = []

        for v in value:
            if v is None:
                msg = "Link cannot be null"
                raise ValueError(msg)

            if isinstance(v, HttpUrl):
                validated_urls.append(v)
                continue

            # Convert string to HttpUrl
            if isinstance(v, str):
                if v.startswith(("http://", "https://")):
                    try:
                        validated_urls.append(HttpUrl(v))
                    except pydantic.ValidationError as e:
                        msg = f"Invalid link format: {e}"
                        raise TypeError(msg)
                elif v in ["localhost", "127.0.0.1"] or cls._validate_ip_address(v):
                    # For local/IP addresses, we'll create an HTTP URL
                    validated_urls.append(HttpUrl(f"http://{v}"))
                else:
                    msg = f"Invalid link format: {v}"
                    raise TypeError(msg)
            else:
                msg = f"Invalid link type: {type(v)}"
                raise TypeError(msg)

        return validated_urls

    @staticmethod
    def _validate_ip_address(ip: str) -> bool:
        """Validate an IP address.

        Args:
            ip (str): The IP address to validate.

        Returns:
            bool: True if the IP address is valid, False otherwise.

        """
        try:
            parts: list[str] = ip.split(".")
            if len(parts) != IP_ADDRESS_PARTS:
                return False

            return all(0 <= int(part) <= MAX_IP_PART_VALUE for part in parts)
        except (ValueError, AttributeError):
            return False

def validate_yaml(file_path: str) -> ValidateConfig:
    """Validate a YAML file.

    Args:
        file_path (str): The path to the YAML file to validate.

    Returns:
        ValidateConfig: The validated YAML data.

    Raises:
        pydantic.ValidationError: If the YAML data is invalid.

    """
    path = Path(file_path)
    with path.open() as file:
        data = yaml.safe_load(file)
    return ValidateConfig.model_validate(data)
