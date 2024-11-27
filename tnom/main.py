import argparse
import asyncio
import logging
import sys
from pathlib import Path

import alerts
import config_load
import database_handler
import dead_man_switch
import query_rand_api
from check_apis import check_apis
from set_up_db import init_and_check_db

ONE_NIBI = 1000000
ZERO_PT_ONE = 100000
CONSECUTIVE_MISSES_THRESHOLD = 3
TOTAL_MISSES_THRESHOLD = 5
CRITICAL_MISSES_THRESHOLD = 10

class MonitoringSystem:
    def __init__(self, config_yml: dict, alert_yml: dict, database_path: Path) -> None:
        """Initialize a MonitoringSystem object.

        Args:
            config_yml (dict): The loaded config YAML file.
            alert_yml (dict): The loaded alert YAML file.
            database_path (Path): The path to the database.

        Attributes:
            config_yml (dict): The loaded config YAML file.
            alert_yml (dict): The loaded alert YAML file.
            database_path (Path): The path to the database.
            consecutive_misses (int): The number of consecutive missed events.
            last_alert_epoch (int | None): The last epoch that alerts were sent.
            alert_sent (dict[str, bool]): A dictionary of alert levels to boolean values
                indicating whether an alert has been sent.

        """
        self.config_yml = config_yml
        self.alert_yml = alert_yml
        self.database_path = database_path
        self.consecutive_misses = 0
        self.last_alert_epoch = None
        self.alert_sent = {
            "consecutive": False,
            "total": False,
            "critical": False,
        }

    def reset_for_new_epoch(self) -> None:
        """Reset monitoring state for new epoch."""
        self.consecutive_misses = 0
        self.alert_sent = {
            "consecutive": False,
            "total": False,
            "critical": False,
        }

    async def process_balance_alerts(
        self,
        query_data: dict,
        current_data: dict) -> None:
        """Handle wallet balance alerts."""
        db_small_bal_alert = current_data["small_balance_alert_executed"]
        db_very_small_bal_alert = current_data["very_small_balance_alert_executed"]

        # Check for low balance conditions
        if query_data["wallet_balance"] < ONE_NIBI and db_small_bal_alert == 0:
            await self._trigger_balance_alert(
                query_data, "high", "Price feeder wallet balance has less than 1 NIBI!",
                "small_balance_alert_executed", 1,
            )

        if query_data["wallet_balance"] < ZERO_PT_ONE and db_very_small_bal_alert == 0:
            await self._trigger_balance_alert(
                query_data, "critical",
                "Price feeder wallet balance has less than 0.1 NIBI!",
                "very_small_balance_alert_executed", 1,
            )

        # Check for balance recovery conditions
        if query_data["wallet_balance"] >= ONE_NIBI and db_small_bal_alert != 0:
            await self._trigger_balance_alert(
                query_data, "info", "Price feeder wallet balance has more than 1 NIBI!",
                "small_balance_alert_executed", 0,
            )

        if query_data["wallet_balance"] >= ZERO_PT_ONE and db_very_small_bal_alert != 0:
            await self._trigger_balance_alert(
                query_data, "info",
                "Price feeder wallet balance has more than 0.1 NIBI!",
                "very_small_balance_alert_executed", 0,
            )

    async def _trigger_balance_alert(self, query_data: dict, level: str,
                                     summary: str, field: str, new_value: int) -> None:
        """Helper method to trigger balance alerts."""
        alert_details = {
            "wallet_balance": (str(query_data["wallet_balance"]), "unibi"),
            "alert_level": level,
        }

        if self.alert_yml["pagerduty_alerts"]:
            alerts.pagerduty_alert_trigger(
                self.alert_yml["routing_key"], alert_details, summary, level,
            )
        if self.alert_yml["telegram_alerts"]:
            alerts.telegram_alert_trigger(
                self.alert_yml["telegram_bot_token"], alert_details,
                self.alert_yml["telegram_chat_id"],
            )

        database_handler.overwrite_single_field(
            self.database_path, query_data["current_epoch"], field, new_value,
        )

    async def process_signing_alerts(
        self,
        epoch: int,
        query_data: dict,
        total_misses: int) -> None:
        """Handle signing event alerts."""
        if self.last_alert_epoch != epoch:
            self.reset_for_new_epoch()
            self.last_alert_epoch = epoch

        if not query_data["check_for_aggregate_votes"]:
            self.consecutive_misses += 1
        else:
            self.consecutive_misses = 0

        alerts_to_send = []

        # Check consecutive misses
        if (self.consecutive_misses >= CONSECUTIVE_MISSES_THRESHOLD
            and not self.alert_sent["consecutive"]):
            alerts_to_send.append({
                "details": {
                    "consecutive_misses": self.consecutive_misses,
                    "alert_level": "high",
                },
                "summary": f"""Alert: {self.consecutive_misses}
                consecutive unsigned events detected!""",
                "severity": "high",
            })
            self.alert_sent["consecutive"] = True

        # Check total misses
        if total_misses >= TOTAL_MISSES_THRESHOLD and not self.alert_sent["total"]:
            alerts_to_send.append({
                "details": {
                    "total_misses": total_misses,
                    "alert_level": "high",
                },
                "summary": f"""Alert: Total unsigned events ({total_misses})
                exceeded threshold!""",
                "severity": "high",
            })
            self.alert_sent["total"] = True

        # Check critical threshold
        if (total_misses >= CRITICAL_MISSES_THRESHOLD
            and not self.alert_sent["critical"]):
            alerts_to_send.append({
                "details": {
                    "total_misses": total_misses,
                    "alert_level": "critical",
                },
                "summary": f"""CRITICAL: Unsigned events ({total_misses})
                at critical level!""",
                "severity": "critical",
            })
            self.alert_sent["critical"] = True

        # Send all accumulated alerts
        for alert in alerts_to_send:
            if self.alert_yml["pagerduty_alerts"]:
                alerts.pagerduty_alert_trigger(
                    self.alert_yml["routing_key"],
                    alert["details"],
                    alert["summary"],
                    alert["severity"],
                )
            if self.alert_yml["telegram_alerts"]:
                alerts.telegram_alert_trigger(
                    self.alert_yml["telegram_bot_token"],
                    alert["details"],
                    self.alert_yml["telegram_chat_id"],
                )

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser with all arguments configured."""
    parser = argparse.ArgumentParser(
        description="Monitoring system for price feeds and wallet balances",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Get default working directory
    working_dir = Path.cwd()

    parser.add_argument(
        "--working-dir",  # Changed from working_dir to working-dir for consistency
        type=str,
        help="The working directory for config files and database\n"
             "Default: current working directory",
        default=working_dir,
        required=False,
    )

    parser.add_argument(
        "--config-path",
        type=str,
        help="Path to the config YAML file\n"
             f"Default: {working_dir}/config.yml",
        default=working_dir / "config.yml",
        required=False,
    )

    parser.add_argument(
        "--alert-path",
        type=str,
        help="Path to the alert YAML file\n"
             f"Default: {working_dir}/alert.yml",
        default=working_dir / "alert.yml",
        required=False,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="v0.3.0",
    )

    return parser

async def main() -> None:
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Convert string paths to Path objects
    working_dir = Path(args.working_dir)
    config_path = Path(args.config_path)
    alert_path = Path(args.alert_path)
    database_path = working_dir / "chain_database" / "tnom.db"

    # Validate paths
    if not config_path.exists():
        logging.error("Config file not found: %s", config_path)
        sys.exit(1)

    if not alert_path.exists():
        logging.error("Alert file not found: %s", alert_path)
        sys.exit(1)

    # Initialize and check the database
    try:
        init_and_check_db(working_dir)
    except Exception as e:
        logging.exception("Failed to initialize database: %s", e)  # noqa: TRY401
        sys.exit(1)

    #  Load the config and alert YAML files
    try:
        config_yml = config_load.load_config_yml(config_path)
        alert_yml = config_load.load_alert_yml(alert_path)
    except Exception as e:
        logging.exception("Failed to load configuration files: %s", e)  # noqa: TRY401
        sys.exit(1)

    # Verify alert configuration
    if not alert_yml["telegram_alerts"] and not alert_yml["pagerduty_alerts"]:
        logging.error("No alerts are enabled! Please enable at least one alert system.")
        sys.exit(1)

    monitoring_system = MonitoringSystem(config_yml, alert_yml, database_path)

    # Create event loop
    loop = asyncio.get_event_loop()

    async def monitoring_loop() -> None:
        """The main loop of the monitoring system.

        This loop runs indefinitely, sleeping for `monitoring_interval` seconds between
        iterations. It checks the APIs, makes a query with a random healthy API,
        processes the query data, writes data to the database, and processes alerts.

        If an exception is raised, the loop will log the exception and sleep for
        10 seconds before continuing.
        """
        while True:
            try:
                # Step three - check APIs
                healthy_apis = await check_apis(config_yml)

                # Step four - Make query with random healthy API
                query_results = await query_rand_api.collect_data_from_random_healthy_api(  # noqa: E501
                    healthy_apis, config_yml)

                # Process query data
                query_data = {
                    "miss_counter": query_results["miss_counter"],
                    "check_for_aggregate_votes": query_results["check_for_aggregate_votes"],  # noqa: E501
                    "current_epoch": query_results["current_epoch"],
                    "wallet_balance": query_results["wallet_balance"],
                }
                # Step five - Write data to database
                # Check if the current_epoch exists in the database
                if database_handler.check_if_epoch_is_recorded(
                    database_path, query_data["current_epoch"]):
                    # Step 5.2a - Update tthe existing db with data

                    # read current epoch data
                    read_crw_data: dict = database_handler.read_current_epoch_data(
                        database_path, query_data["current_epoch"])
                    db_unsigned_or_ev: int = read_crw_data["unsigned_oracle_events"]
                    db_small_bal_alert: int = (
                        read_crw_data["small_balance_alert_executed"])
                    db_very_small_bal_alert: int = (
                        read_crw_data["very_small_balance_alert_executed"])
                    # if the check failed the return should be false adding +1 to not
                    # signing events
                    if query_data["check_for_aggregate_votes"] is False:
                        db_unsigned_or_ev += 1
                    insert_data: dict[int] = {
                        "slash_epoch": query_data["current_epoch"],
                        "miss_counter_events": query_data["miss_counter"],
                        "unsigned_oracle_events": db_unsigned_or_ev,
                        "price_feed_addr_balance": query_data["wallet_balance"],
                        "small_balance_alert_executed": db_small_bal_alert,
                        "very_small_balance_alert_executed": db_very_small_bal_alert,
                    }
                    database_handler.write_epoch_data(database_path, insert_data)
                elif database_handler.check_if_epoch_is_recorded(
                    database_path, query_data["current_epoch"]) is False:
                    # Step 5.2b if no db, no current epoch entered or just starting for
                    # first time

                    # make the new entry in the db

                    # check if there is a previous entry
                    if database_handler.check_if_epoch_is_recorded(
                    database_path, query_data["current_epoch"] - 1):
                        read_prev_crw_data : dict = database_handler.read_current_epoch_data(  # noqa: E501
                            database_path, query_data["current_epoch"] - 1)
                        if (read_prev_crw_data["slash_epoch"]
                            == query_data["current_epoch"] - 1):
                            prev_small_bal_alert: int = read_prev_crw_data[
                                "small_balance_alert_executed"]
                            prev_very_small_bal_alert: int = read_prev_crw_data[
                                "very_small_balance_alert_executed"]
                    elif database_handler.check_if_epoch_is_recorded(
                        database_path, query_data["current_epoch"] - 1) is False:
                        prev_small_bal_alert = 0
                        prev_very_small_bal_alert = 0
                    insert_data: dict[int] = {
                        "slash_epoch": query_data["current_epoch"],
                        "miss_counter_events": query_data["miss_counter"],
                        "unsigned_oracle_events": 0,
                        "price_feed_addr_balance": query_data["wallet_balance"],
                        "small_balance_alert_executed": prev_small_bal_alert,
                        "very_small_balance_alert_executed": prev_very_small_bal_alert,
                    }
                    database_handler.write_epoch_data(database_path, insert_data)
                     # Process alerts
                await monitoring_system.process_balance_alerts(query_data, insert_data)
                await monitoring_system.process_signing_alerts(
                    query_data["current_epoch"],
                    query_data,
                    insert_data["unsigned_oracle_events"],
                )

                # Sleep for interval
                await asyncio.sleep(config_yml.get("monitoring_interval", 60))

            except Exception as e:  # noqa: PERF203
                logging.exception("Error in monitoring loop: %s", e)  # noqa: TRY401
                await asyncio.sleep(10)
                # To do reaserch RuffPERF203
# Run monitoring and health check concurrently
    tasks = [
        monitoring_loop(),
        asyncio.to_thread(
            dead_man_switch.run_health_check,
            alert_yml["health_check_url"],
            alert_yml["health_check_interval"],
            None,
        ) if alert_yml["health_check_enabled"] else None,
    ]

    # Filter out None tasks and run
    tasks = [t for t in tasks if t is not None]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logging.info("Shutting down monitoring...")
    finally:
        loop.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down monitoring...")
        sys.exit(0)
