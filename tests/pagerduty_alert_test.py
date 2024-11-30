import unittest
from unittest.mock import patch

import yaml

from tnom.alerts import pagerduty_alert_trigger


class TestPagerDutyAlertTrigger(unittest.TestCase):
    def setUp(self):
        # Properly load the YAML file and close it
        with open("alert.yml", "r") as file:
            config = yaml.safe_load(file)

        # Correctly access the routing key
        self.routing_key = config["pagerduty_routing_key"]
        # Sample alert details for testing
        self.sample_alert = {
            "alert_details": {
                "error_type": "Test Alert",
                "additional_info": "This is a test alert from unittest"
            },
            "summary": "Unittest PagerDuty Alert Test",
            "severity": "warning"
        }

    def test_successful_alert_trigger(self):
        """Test a successful PagerDuty alert trigger.

        Requires a valid routing key.
        """
        if not self.routing_key:
            self.skipTest("No PagerDuty routing key found. Skipping real alert test.")

        dedup_key = pagerduty_alert_trigger(
            routing_key=self.routing_key,
            alert_details=self.sample_alert["alert_details"],
            summary=self.sample_alert["summary"],
            severity=self.sample_alert["severity"]
        )

        # Check that a deduplication key is returned
        self.assertIsNotNone(dedup_key, "Failed to trigger PagerDuty alert")

    @patch("pdpyras.EventsAPISession.trigger")
    def test_alert_trigger_with_mock(self, mock_trigger) -> None:
        """Test alert trigger using a mock to simulate different scenarios."""
        # Simulate a successful response
        mock_trigger.return_value = {"dedup_key": "mock_dedup_key"}

        dedup_key = pagerduty_alert_trigger(
            routing_key="mock_routing_key",
            alert_details=self.sample_alert["alert_details"],
            summary=self.sample_alert["summary"],
            severity=self.sample_alert["severity"]
        )

        # Verify the mock was called and returned the expected result
        mock_trigger.assert_called_once()
        self.assertEqual(dedup_key, "mock_dedup_key")

    def test_alert_trigger_with_invalid_severity(self):
        """Test alert trigger with an invalid severity level."""
        with self.assertRaises(ValueError):
            pagerduty_alert_trigger(
                routing_key=self.routing_key,
                alert_details=self.sample_alert["alert_details"],
                summary=self.sample_alert["summary"],
                severity="invalid_severity"
            )

if __name__ == "__main__":
    unittest.main()
