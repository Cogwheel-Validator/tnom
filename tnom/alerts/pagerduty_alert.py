"""Functions for triggering alerts on PagerDuty.

There is one function:
    - pagerduty_alert_trigger: Triggers a PagerDuty alert with the given arguments.

Usage:
    Used to trigger alerts on PagerDuty.
"""

from __future__ import annotations

import logging
from typing import Any

from pdpyras import EventsAPISession

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def pagerduty_alert_trigger(
    routing_key: str,
    alert_details: dict[str, Any],
    summary: str,
    severity: str,
) -> str | None:
    """Triggers a PagerDuty alert with the given arguments.

    Args:
        routing_key (str): The routing key used to authenticate the trigger request.
        alert_details (dict[str, Any]): Additional details about the alert.
        summary (str): A summary of the alert.
        severity (str): The severity level of the alert.

    Returns:
        str | None:
        The deduplication key of the triggered alert,
        or None if the alert failed to trigger.

    """
    session = EventsAPISession(routing_key=routing_key)
    try:
        response = session.trigger(
            summary=summary,
            source="Nibiru Oracle Monitor",
            severity=severity,
            custom_details=alert_details,
        )
        return response.get("dedup_key")
    except Exception as e:
        logger.exception("Failed to trigger PagerDuty alert:", exc_info=e)
        return None
