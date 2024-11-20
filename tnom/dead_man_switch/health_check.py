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

import logging
import time

import requests
import schedule


def dead_man_switch_trigger(dead_man_switch_url: str) -> None:
    """Triggers a dead man switch at the given URL.

    Args:
        dead_man_switch_url (str): The URL of the dead man switch to trigger.

    Returns:
        None

    """
    try:
        requests.head(dead_man_switch_url, timeout=1)
    except requests.RequestException:
        logging.exception("Failed to trigger dead man switch.")

# TO DO TEST THIS FUNC OUT
def run_health_check(
    dead_man_switch_url: str,
    interval: int,
    max_iterations: int | None) -> None:
    """Triggers a dead man switch at the given URL at regular intervals.

    Args:
        dead_man_switch_url (str): The URL of the dead man switch to trigger.
        interval (int): The interval in seconds between each dead man switch trigger.
        max_iterations (int | None): The maximum number of iterations. If None,
        the loop will run indefinitely.

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

    schedule.every(interval).seconds.do(dead_man_switch_trigger, dead_man_switch_url)

    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        schedule.run_pending()
        time.sleep(1.0)
        iteration += 1

    # Clear the scheduled job when done
    schedule.clear()
