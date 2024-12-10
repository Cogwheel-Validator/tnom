"""Check if APIs are online functional."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import query

MAX_BLOCK_HEIGHT_DIFF = 25

async def check_apis(load_config: dict[str, Any]) -> list[str]:
    """Check if the APIs are online functional.

    Args:
        load_config (dict[str, Any]): The loaded configuration from the YAML file.

    Returns:
        list[str]: The list of healthy APIs.

    """
    async with aiohttp.ClientSession() as session:
        loaded_apis = load_config["APIs"]
        tasks = [query.check_latest_block(api, session) for api in loaded_apis]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        # Fully functional APIs
        online_apis_with_data = [(api, response) for api, response in zip(
            loaded_apis, responses) if not isinstance(response, Exception)
                                 and response is not None]
        # Unhealthy APIs
        unhealthy_apis = [api for api, response in zip(
            loaded_apis, responses) if isinstance(response, Exception)
                          or response is None]

        if not online_apis_with_data:
            logging.warning("No healthy APIs found")
            logging.info("Unhealthy APIs: %s", unhealthy_apis)
            return []

        max_block_height = max(api_data[0] for _, api_data in online_apis_with_data)

        healthy_apis = [api for api, (block_height, _) in online_apis_with_data
                       if max_block_height - block_height <= MAX_BLOCK_HEIGHT_DIFF]

        logging.info("Healthy APIs: %s\nUnhealthy APIs: %s",
                    healthy_apis, unhealthy_apis)
        return healthy_apis
