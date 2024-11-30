"""Functions for triggering alerts on PagerDuty.

There is one function:
    - pagerduty_alert_trigger: Triggers a PagerDuty alert with the given arguments.

Usage:
    Used to trigger alerts on PagerDuty.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pdpyras import EventsAPISession

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def validate_severity(severity: str) -> str:
    """Validate and normalize the severity level.

    Args:
        severity (str): The input severity level.

    Returns:
        str: Normalized severity level.

    Raises:
        ValueError: If the severity is not valid.

    """
    valid_severities = ["critical", "error", "warning", "info"]
    normalized_severity = severity.lower()

    if normalized_severity not in valid_severities:
        msg = f"Invalid severity. Must be one of {valid_severities}"
        raise ValueError(msg)

    return normalized_severity

def pagerduty_alert_trigger(
    routing_key: str,
    alert_details: dict[str, Any],
    summary: str,
    severity: str,
) -> Optional[str]:  # noqa: UP007
    # Use Optional for now untill it is fixed
    """Triggers a PagerDuty alert with the given arguments.

    Args:
        routing_key (str): The routing key used to authenticate the trigger request.
        alert_details (dict[str, Any]): Additional details about the alert.
        summary (str): A summary of the alert.
        severity (str): The severity level of the alert.

    Returns:
        Optional[str]: The deduplication key of the triggered alert,
        or None if the alert failed to trigger.

    """
    try:
        # Validate severity first
        normalized_severity = validate_severity(severity)

        # Create session
        session = EventsAPISession(routing_key)# Trigger the alert
        response = session.trigger(
            summary=summary,
            source="Nibiru Oracle Monitor",
            severity=normalized_severity,
            custom_details=alert_details,
        )

        # Log the response
        logger.info("PagerDuty response: %s", response)

        # Ensure we're getting the dedup_key correctly
        if isinstance(response, dict):
            return response.get("dedup_key")
        elif isinstance(response, str):
            return response
        else:
            return None

    except ValueError as ve:
        # Handle severity validation errors
        logger.error(f"Severity validation error: {ve}")  # noqa: TRY400, G004
        raise
    except Exception as e:
        # Log and re-raise other exceptions
        logger.exception("Failed to trigger PagerDuty alert:", exc_info=e)
        raise
