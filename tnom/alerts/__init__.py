"""Alert triggers for various platforms.

This package provides functions for triggering alerts on PagerDuty and Telegram.
"""
from .pagerduty_alert import pagerduty_alert_trigger
from .telegram_alert import telegram_alert_trigger

__all__ = ["pagerduty_alert_trigger", "telegram_alert_trigger"]
