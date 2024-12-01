import asyncio
import unittest

import yaml

from tnom.alerts import telegram_alert_trigger


class TelegramAlertTest(unittest.TestCase):
    def setUp(self):
        with open("alert.yml", "r") as file:
            config = yaml.safe_load(file)
        self.telegram_bot_token = config.get("telegram_bot_token")
        self.chat_id = config.get("telegram_chat_id")
        self.alert_details = {
            "error_type": "Test Alert",
            "additional_info": "This is a test alert."
        }

    def test_send_test_message(self):
        """Test sending a Telegram alert message."""
        async def send_test_message():
            try:
                result = await telegram_alert_trigger(
                    self.telegram_bot_token,
                    self.alert_details,
                    self.chat_id,
                )
                return result
            except Exception as e:
                self.fail(f"Failed to send Telegram alert: {e}")

        # Use asyncio to run the async function it might run the function?
        result = asyncio.run(send_test_message())

        # Optional: Add an assertion to check the result
        self.assertIsNotNone(result, "Telegram message was not sent")


if __name__ == "__main__":
    unittest.main()