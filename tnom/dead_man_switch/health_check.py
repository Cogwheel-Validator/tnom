"""The dead_man_switch package.

The dead_man_switch package provides functions for triggering a dead man switch.

In this package, the functions are:
    - dead_man_switch_trigger: Triggers a dead man switch at the given URL.
    - run_health_check: Starts an infinite loop which triggers a dead man switch
    at the given URL every given interval.

Usage:
    Used to trigger a dead man switch.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from http import HTTPStatus

import aiohttp


async def dead_man_switch_trigger(url: str) -> None:
    """Async function to trigger dead man switch.

    Args:
        url (str): The URL to trigger the dead man switch.

    Returns:
        None

    """
    try:
        async with (aiohttp.ClientSession() as session,
                    session.get(url, timeout=10) as response):
                if response.status == HTTPStatus.OK:
                    logging.info("Health check ping successful.")
                else:
                    logging.warning(
                        "Health check ping failed. Status code: %s", response.status)
    except Exception as e:
        logging.exception("Error in health check ping: %s", e)  # noqa: TRY401



async def run_health_check(
    dead_man_switch_url: str,
    interval: int,
    max_iterations: int | None,
    shutdown_event: asyncio.Event,
    ) -> None:
    """Triggers a dead man switch at the given URL at regular intervals.

    Args:
        dead_man_switch_url (str): The URL of the dead man switch to trigger.
        interval (int): The interval in seconds between each dead man switch trigger.
        max_iterations (int | None): The maximum number of iterations. If None,
        the loop will run indefinitely.
        shutdown_event (asyncio.Event): The event to signal when the loop should
        stop.

    Returns:
        None

    Raises:
        TypeError: If dead_man_switch_url is not a string or interval is not an integer.
        ValueError: If interval is less than or equal to zero.

    """
    if not isinstance(dead_man_switch_url, str):
        msg = "dead_man_switch_url must be a string"
        raise TypeError(msg)
    if not isinstance(interval, int):
        msg = "interval must be an integer"
        raise TypeError(msg)
    if interval <= 0:
        msg = "interval must be greater than zero"
        raise ValueError(msg)

    iteration = 0
    try:
        while not shutdown_event.is_set():
            # Check for max iterations if specified
            if max_iterations is not None and iteration >= max_iterations:
                break

            # Trigger health check
            await dead_man_switch_trigger(dead_man_switch_url)

            # Wait for the interval or until shutdown is signaled
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=interval,
                )

            iteration += 1

    except asyncio.CancelledError:
        logging.info("Health check task was cancelled.")
    except Exception as e:
        logging.exception("Error in health check: %s", e)  # noqa: TRY401
    finally:
        logging.info("Health check task shutting down.")
