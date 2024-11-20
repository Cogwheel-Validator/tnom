"""Telegram alert trigger module.

There is one function:
    - telegram_alert_trigger: Triggers a Telegram alert with the given arguments.

Usage:
    Used to trigger alerts on Telegram.
"""
from __future__ import annotations

import logging
from typing import Any

import telegram
import yaml
from telegram import Bot


async def telegram_alert_trigger(
    telegram_bot_token: str,
    alert_details: dict[str, Any],
    chat_id: str,
) -> telegram.Message | None:
    """Triggers a Telegram alert with the given arguments.

    Args:
        telegram_bot_token (str): The token used to authenticate the Telegram bot.
        alert_details (dict[str, Any]): Additional details about the alert.
        chat_id (str): The ID of the chat where the alert will be sent.

    Returns:
        telegram.Message | None: The sent message object, or None if the alert failed to
        send.

    """
    # Type checking
    if not isinstance(telegram_bot_token, str):
        msg = "telegram_bot_token must be a string"
        raise TypeError(msg)
    if not isinstance(alert_details, dict):
        msg = "alert_details must be a dictionary"
        raise TypeError(msg)
    if not isinstance(chat_id, str):
        msg = "chat_id must be a string"
        raise TypeError(msg)
    # Logic
    try:
        bot = Bot(telegram_bot_token)
        # Convert alert details to string
        details_to_str = "```\n" + yaml.dump( # turn dict into yaml and dump it?
            # Future note: look for some better solution later
            alert_details, default_flow_style=False) + "\n```"
        return await bot.send_message(chat_id=chat_id, text=details_to_str)
    except Exception as e:
        if isinstance(e, (telegram.error.TelegramError, telegram.error.NetworkError)):
            logging.exception("Error sending Telegram alert:")
            return None
        raise
