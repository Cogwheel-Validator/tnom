import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

import alerts
import config_load
import database_handler
import dead_man_switch
import prometheus_client_endpoint as prom
import query_rand_api
from check_apis import check_apis
from set_up_db import init_and_check_db

ONE_NIBI = 1000000
ZERO_PT_ONE = 100000
CONSECUTIVE_MISSES_THRESHOLD = 3
P2_UNSIGNED_EV_THR = 10
P1_UNSIGNED_EV_THR = 20
API_CONS_MISS_THRESHOLD = 3

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
            api_consecutive_misses (int): The number of consecutive API was unavailable.
            alert_sent (dict[str, bool]): A dictionary of alert levels to boolean values
                indicating whether an alert has been sent.

        """
        self.config_yml = config_yml
        self.alert_yml = alert_yml
        self.database_path = database_path
        self.consecutive_misses = 0
        self.last_alert_epoch = None
        self.api_consecutive_misses = 0
        self.alert_sent = {
            "consecutive": False,
            "total": False,
            "critical": False,
            "healthy_api_missing": False,
        }

    def reset_for_new_epoch(self) -> None:
        """Reset monitoring state for new epoch."""
        self.consecutive_misses = 0
        self.alert_sent = {
            "consecutive": False,
            "total": False,
            "critical": False,
            "healthy_api_missing": False,
        }

    # This parameter is related to the miss counter events which is not the same as
    # the unsigning events. During the process of testing the script I was not able
    # to reproduce missing event. I think it is related to missing when the oracle
    # is voting price higher/lower then rest of the validators.
    # For now alerts will be placed until there is a possibility to test it out, but
    # it is not 100%\ sure it will work as I haven't seen it ever captured.
    # TO DO in the future clear the naming since it will probably create confusion
    # wit the current missing of signing events.
    async def process_miss_parameter_alerts(
        self,
        query_data: dict,
        current_data: dict) -> None:
        """Handle miss parameter alerts."""
        # Tresholds are set at random since I couldn't execute it in the test
        thresholds = [
            ("miss_counter_p3_executed", 10, "warning"),
            ("miss_counter_p2_executed", 25, "critical"),
            ("miss_counter_p1_executed", 50, "critical"),
        ]

        for field, threshold, level in thresholds:
            if (int(current_data["miss_counter_events"]) > threshold and
                current_data[field] == 0):
                await self._trigger_miss_parameter_alert(
                    query_data, current_data, level,
                    f"Current miss event is above {threshold}",
                    field, 1,
                )

    async def _trigger_miss_parameter_alert(
        self,
        query_data: dict,
        current_data: dict,
        alert_level: str,
        summary: str,
        field: str,
        new_value: int) -> None:
            """Helper method to trigger miss parameter alerts."""
            alert_details = {
                "miss_counter": (str(current_data["miss_counter"]), "events"),
                "alert_level": alert_level,
            }
            if self.alert_yml.get("pagerduty_alerts") is True:
                pd_details = alert_details.copy()
                await asyncio.gather(
                    alerts.pagerduty_alert_trigger(
                        self.alert_yml["pagerduty_routing_key"],
                        pd_details,
                        summary,
                        alert_level,
                    ),
                    database_handler.overwrite_single_field(
                        self.database_path, query_data["current_epoch"], field, new_value,
                    ),
                )
            if self.alert_yml.get("telegram_alerts") is True:
                tg_details = alert_details.copy()
                await asyncio.gather(
                    alerts.telegram_alert_trigger(
                        self.alert_yml["telegram_bot_token"], tg_details,
                        self.alert_yml["telegram_chat_id"],
                    ),
                    database_handler.overwrite_single_field(
                        self.database_path, query_data["current_epoch"], field, new_value,
                    ),
                )

    async def process_balance_alerts(
        self,
        query_data: dict,
        current_data: dict) -> None:
        """Handle wallet balance alerts."""
        balance_alerts = [
            {
                "threshold": ONE_NIBI,
                "executed_field": "small_balance_alert_executed",
                "critical_message":
                    "Price feeder wallet balance has less than 1 NIBI!",
                "recovery_message":
                    "Price feeder wallet balance has more than 1 NIBI!",
            },
            {
                "threshold": ZERO_PT_ONE,
                "executed_field": "very_small_balance_alert_executed",
                "critical_message":
                    "Price feeder wallet balance has less than 0.1 NIBI!",
                "recovery_message":
                    "Price feeder wallet balance has more than 0.1 NIBI!",
            },
        ]

        for alert in balance_alerts:
            executed = current_data[alert["executed_field"]]
            if query_data["wallet_balance"] < alert["threshold"] and executed == 0:
                await self._trigger_balance_alert(
                    query_data, "critical", alert["critical_message"],
                    alert["executed_field"], 1,
                )
            elif query_data["wallet_balance"] >= alert["threshold"] and executed != 0:
                await self._trigger_balance_alert(
                    query_data, "info", alert["recovery_message"],
                    alert["executed_field"], 0,
                )

    async def _trigger_balance_alert(self, query_data: dict, level: str,
                                     summary: str, field: str, new_value: int) -> None:
        """Helper method to trigger balance alerts."""
        alert_details = {
            "wallet_balance": (str(query_data["wallet_balance"]), "unibi"),
            "alert_level": level,
        }

        if self.alert_yml.get("pagerduty_alerts") is True:
            alerts.pagerduty_alert_trigger(
                self.alert_yml["pagerduty_routing_key"], alert_details, summary, level,
            )
        if self.alert_yml.get("telegram_alerts") is True:
            await alerts.telegram_alert_trigger(
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
        """Process the signing alerts for the given epoch and query data.

        This function resets the counts and flags for the given epoch if the epoch
        has changed, then checks the consecutive and total misses for the given
        epoch against the thresholds. If the thresholds are exceeded, it sends
        alerts to the configured channels.

        Args:
            epoch (int): The current epoch.
            query_data (dict): The query data for the current epoch.
            total_misses (int): The total number of misses for the current epoch.

        """
        if self.last_alert_epoch != epoch:
            self.reset_for_new_epoch()
            self.last_alert_epoch = epoch

        previous_data = database_handler.read_current_epoch_data(
        self.database_path, epoch)

        if previous_data is None:
            self.consecutive_misses = (1 if not
                                       query_data["check_for_aggregate_votes"] else 0)
        elif not query_data["check_for_aggregate_votes"]:
            self.consecutive_misses = previous_data.get("consecutive_misses", 0) + 1
        else:
            self.consecutive_misses = 0

        alerts_to_send = []

        # Check consecutive misses
        if (self.consecutive_misses >= CONSECUTIVE_MISSES_THRESHOLD
            and not self.alert_sent["consecutive"]):
            alerts_to_send.append({
                "details": {
                    "consecutive_misses": self.consecutive_misses,
                    "alert_level": "critical",
                },
                "summary": f"""Alert: {self.consecutive_misses}
                consecutive unsigned events detected!""",
                "severity": "critical",
            })
            self.alert_sent["consecutive"] = True

        # Check total misses
        if total_misses >= P2_UNSIGNED_EV_THR and not self.alert_sent["total"]:
            alerts_to_send.append({
                "details": {
                    "total_misses": total_misses,
                    "alert_level": "critical",
                },
                "summary": f"""Alert: Total unsigned events ({total_misses})
                exceeded threshold!""",
                "severity": "critical",
            })
            self.alert_sent["total"] = True

        # Check critical threshold
        if (total_misses >= P1_UNSIGNED_EV_THR
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

        # Store consecutive misses count in database
        database_handler.overwrite_single_field(
            self.database_path,
            epoch,
            "consecutive_misses",
            self.consecutive_misses,
        )

        # Send all accumulated alerts
        for alert in alerts_to_send:
            if self.alert_yml.get("pagerduty_alerts") is True:
                alerts.pagerduty_alert_trigger(
                    self.alert_yml["pagerduty_routing_key"],
                    alert["details"],
                    alert["summary"],
                    alert["severity"],
                )
            if self.alert_yml.get("telegram_alerts") is True:
                await alerts.telegram_alert_trigger(
                    self.alert_yml["telegram_bot_token"],
                    alert["details"],
                    self.alert_yml["telegram_chat_id"],
                )

    async def process_api_not_working(
        self,
        epoch: int,
        *,
        no_healthy_apis: bool = True) -> None:
        """Process no healthy APIs alert.

        This function processes alert for no healthy APIs. If no_healthy_apis is True,
        it increments the counter of consecutive misses of APIs and sends a warning
        log message. If no_healthy_apis is False, it checks if the counter of
        consecutive misses is above the threshold and sends a recovery alert if it
        is. Then it resets the counter and the alert flag.

        Args:
            epoch (int): The epoch number.
            no_healthy_apis (bool): If no healthy APIs are present. Defaults to True.

        """
        if self.last_alert_epoch != epoch:
            self.reset_for_new_epoch()
            self.last_alert_epoch = epoch

        api_consecutive_misses = self.api_consecutive_misses
        if no_healthy_apis is True:
            api_consecutive_misses += 1
            logging.warning("Warning API not working for %s times!",
                            api_consecutive_misses)
        elif no_healthy_apis is False:
            # Check if we need to send recovery alert
            if (self.api_consecutive_misses >= API_CONS_MISS_THRESHOLD
                and self.alert_sent["healthy_api_missing"] is True):
                summary = "Alert: API working again!"
                level = "info"
                alert_details = {
                    "api_consecutive_misses": api_consecutive_misses,
                    "alert_level": "info",
                }
                if self.alert_yml.get("pagerduty_alerts") is True:
                    alerts.pagerduty_alert_trigger(
                        self.alert_yml["pagerduty_routing_key"],
                        alert_details,
                        summary,
                        level,
                    )
                if self.alert_yml.get("telegram_alerts") is True:
                    await alerts.telegram_alert_trigger(
                        self.alert_yml["telegram_bot_token"],
                        alert_details,
                        self.alert_yml["telegram_chat_id"],
                    )
            # Reset counter and alert flag after sending recovery alert
            api_consecutive_misses = 0
            self.alert_sent["healthy_api_missing"] = False

        self.api_consecutive_misses = api_consecutive_misses

        # Send alert for API down
        if (api_consecutive_misses >= API_CONS_MISS_THRESHOLD and
            not self.alert_sent["healthy_api_missing"]):
                summary = "Alert: API not working!"
                level = "critical"
                alert_details = {
                    "api_consecutive_misses": api_consecutive_misses,
                    "alert_level": "critical",
                }
                if self.alert_yml.get("pagerduty_alerts") is True:
                    alerts.pagerduty_alert_trigger(
                        self.alert_yml["pagerduty_routing_key"],
                        alert_details,
                        summary,
                        level,
                    )
                if self.alert_yml.get("telegram_alerts") is True:
                    await alerts.telegram_alert_trigger(
                        self.alert_yml["telegram_bot_token"],
                        alert_details,
                        self.alert_yml["telegram_chat_id"],
                    )
                self.alert_sent["healthy_api_missing"] = True

        # Store data in the database
        # TO DO decide if this will be needed in the upcoming versions
        database_handler.overwrite_single_field(
            self.database_path,
            epoch,
            "api_cons_miss",
            self.api_consecutive_misses,
        )

def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser with all arguments configured."""
    parser = argparse.ArgumentParser(
        description="Monitoring tool for tracking Nibiru oracle price feeder.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Get default working directory
    working_dir = Path.cwd()

    parser.add_argument(
        "--working-dir",
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
             f"Default always looks to the current dir: {working_dir}/config.yml",
        default=working_dir / "config.yml",
        required=False,
    )

    parser.add_argument(
        "--alert-path",
        type=str,
        help="Path to the alert YAML file\n"
             f"Default always looks to the current dir: {working_dir}/alert.yml",
        default=working_dir / "alert.yml",
        required=False,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="v0.5.2",
    )

    parser.add_argument(
            "--prometheus-host",
            type=str,
            help="Prometheus host to run on\n"
                "Overrides host in alert config file\n"
                "Default: 127.0.0.1 if not specified in config",
            required=False,
    )

    parser.add_argument(
        "--prometheus-port",
        type=int,
        help="Prometheus port to run on\n"
             "Overrides port in alert config file\n"
             "Default: 7130 if not specified in config",
        required=False,
    )

    return parser

async def main() -> None:
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
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
        # if it exists see if schema is ok
        database_handler.check_and_update_database_schema(database_path)
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

    # Determine Prometheus host and port
    prometheus_host : str = (args.prometheus_host
                       or alert_yml.get("prometheus_host"))
    prometheus_port : int = (args.prometheus_port
                       or alert_yml.get("prometheus_port"))

    monitoring_system = MonitoringSystem(config_yml, alert_yml, database_path)

    shutdown_event = asyncio.Event()

    async def graceful_shutdown(tasks: list) -> None:
        """Perform a more controlled shutdown of tasks.

        Args:
            tasks (list): List of running tasks to shut down

        """
        if not tasks:
            return

        # First, cancel all tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete, but with a timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=10.0,
                # Set timeout to 10 secounds, maybe set to 60 in the future?
            )
        except asyncio.TimeoutError:
            logging.warning("Some tasks did not shut down within the timeout.")
        except Exception as e:
            logging.exception("Error during shutdown: %s", e)

    async def monitoring_loop() -> None:
        """The main loop of the monitoring system.

        This loop runs indefinitely, sleeping for `monitoring_interval` seconds between
        iterations. It checks the APIs, makes a query with a random healthy API,
        processes the query data, writes data to the database, and processes alerts.

        If an exception is raised, the loop will log the exception and sleep for
        10 seconds before continuing.
        """
        try:
            while True:
                try:
                    # Step three - check APIs
                    latest_epoch = (
                            database_handler.read_last_recorded_epoch(database_path))
                    healthy_apis = await check_apis(config_yml)
                    while not healthy_apis:
                        logging.error("Failed to check APIs")
                        await monitoring_system.process_api_not_working(
                            latest_epoch, no_healthy_apis=True)
                        # stop the script here and start from while True again until there
                        # is a healthy api
                        await asyncio.sleep(config_yml.get("monitoring_interval", 60))
                        healthy_apis = await check_apis(config_yml)
                    # this is needed to revert the consecutive_misses counter
                    if healthy_apis:
                        await monitoring_system.process_api_not_working(
                            latest_epoch, no_healthy_apis=False)

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
                        logging.info("Writing data in the existing epoch")
                        # Step 5.2a - Update the existing db with data

                        # read current epoch data
                        read_crw_data: dict = database_handler.read_current_epoch_data(
                            database_path, query_data["current_epoch"])
                        db_unsigned_or_ev: int = read_crw_data["unsigned_oracle_events"]
                        db_small_bal_alert: int = (
                            read_crw_data["small_balance_alert_executed"])
                        db_very_small_bal_alert: int = (
                            read_crw_data["very_small_balance_alert_executed"])
                        db_consecutive_misses: int = read_crw_data["consecutive_misses"]
                        db_miss_counter_p1_executed : int = read_crw_data[
                            "miss_counter_p1_executed"]
                        db_miss_counter_p2_executed : int = read_crw_data[
                            "miss_counter_p2_executed"]
                        db_miss_counter_p3_executed : int = read_crw_data[
                            "miss_counter_p3_executed"]
                        db_api_cons_miss : int = read_crw_data["api_cons_miss"]
                        # if the check failed the return should be false adding +1 to not
                        # signing events
                        if query_data["check_for_aggregate_votes"] is False:
                            db_unsigned_or_ev += 1
                            logging.info(f"Incrementing unsigned events to: {db_unsigned_or_ev}")
                        insert_data: dict[int] = {
                            "slash_epoch": query_data["current_epoch"],
                            "miss_counter_events": query_data["miss_counter"],
                            "miss_counter_p1_executed": db_miss_counter_p1_executed,
                            "miss_counter_p2_executed": db_miss_counter_p2_executed,
                            "miss_counter_p3_executed": db_miss_counter_p3_executed,
                            "unsigned_oracle_events": db_unsigned_or_ev,
                            "price_feed_addr_balance": query_data["wallet_balance"],
                            "small_balance_alert_executed": db_small_bal_alert,
                            "very_small_balance_alert_executed": db_very_small_bal_alert,
                            "consecutive_misses": db_consecutive_misses,
                            "api_cons_miss": db_api_cons_miss,
                        }
                        database_handler.write_epoch_data(database_path, insert_data)
                    elif database_handler.check_if_epoch_is_recorded(
                        database_path, query_data["current_epoch"]) is False:
                        logging.info("Writing data in a new epoch")
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
                                prev_consecutive_misses: int = read_prev_crw_data[
                                    "consecutive_misses"]
                        elif database_handler.check_if_epoch_is_recorded(
                            database_path, query_data["current_epoch"] - 1) is False:
                            prev_small_bal_alert = 0
                            prev_very_small_bal_alert = 0
                            prev_consecutive_misses = 0
                        insert_data: dict[int] = {
                            "slash_epoch": query_data["current_epoch"],
                            "miss_counter_events": query_data["miss_counter"],
                            "miss_counter_p1_executed": 0,
                            "miss_counter_p2_executed": 0,
                            "miss_counter_p3_executed": 0,
                            "unsigned_oracle_events": 0,
                            "price_feed_addr_balance": query_data["wallet_balance"],
                            "small_balance_alert_executed": prev_small_bal_alert,
                            "very_small_balance_alert_executed": prev_very_small_bal_alert,
                            "consecutive_misses": prev_consecutive_misses,
                            "api_cons_miss": 0,
                        }
                        database_handler.write_epoch_data(database_path, insert_data)
                    # Process alerts
                    await monitoring_system.process_balance_alerts(query_data, insert_data)
                    await monitoring_system.process_signing_alerts(
                        query_data["current_epoch"],
                        query_data,
                        insert_data["unsigned_oracle_events"],
                    )
                    await monitoring_system.process_miss_parameter_alerts(
                        query_data, insert_data,
                    )
                    # Check for shutdown between major operations
                    if shutdown_event.is_set():
                        break
                    # Sleep for interval
                    await asyncio.sleep(config_yml.get("monitoring_interval", 60))
                except Exception as e:
                    if not shutdown_event.is_set():
                        logging.exception("Error in monitoring loop: %s", e)
                        await asyncio.sleep(10)
                    else:
                        break
        except asyncio.CancelledError:
            logging.info("Monitoring loop cancelled.")
        finally:
            logging.info("Monitoring loop shutting down gracefully.")
                    # To do reaserch RuffPERF203

    async def health_check_task() -> None:
        """Runs the health check task asynchronously.

        This task executes the `run_health_check` function in a separate thread
        if health checks are enabled in the alert configuration. It monitors the
        health of a service by periodically triggering a dead man switch.

        Raises:
            asyncio.CancelledError: If the task is cancelled during execution.

        """
        try:
            if alert_yml["health_check_enabled"]:
                await dead_man_switch.run_health_check(
                    alert_yml["health_check_url"],
                    alert_yml["health_check_interval"],
                    None,
                    shutdown_event,
                )
        except asyncio.CancelledError:
            logging.info("Health check task cancelled.")
        finally:
            logging.info("Health check task shutting down gracefully.")

    # Create a single shutdown handler
    def handle_shutdown() -> None:
        """Shutdown signal handler.

        Set the shutdown event when a shutdown signal is received,
        unless the event is already set.
        """
        if not shutdown_event.is_set():
            logging.info("Shutdown signal received. Stopping tasks...")
            shutdown_event.set()

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown)

    # Prepare tasks
    tasks = []
    try:
        # Create tasks
        monitoring_task = asyncio.create_task(monitoring_loop())
        tasks.append(monitoring_task)

        if alert_yml["health_check_enabled"]:
            health_check_task_obj = asyncio.create_task(health_check_task())
            tasks.append(health_check_task_obj)

        if alert_yml["prometheus_client_enabled"]:
            latest_epoch = database_handler.read_last_recorded_epoch(database_path)
            prometheus = prom.PrometheusMetrics(database_path, latest_epoch)
            prometheus_task = asyncio.create_task(
                prom.start_metrics_server(
                    prometheus,
                    prometheus_host,
                    prometheus_port,
                    shutdown_event,
                    database_path,
                    config_yml["monitoring_interval"],
                ),
            )
            tasks.append(prometheus_task)

        # Wait for tasks or shutdown
        await shutdown_event.wait()

    except Exception as e:
        logging.exception("Unexpected error: %s", e)
    finally:
        # Perform graceful shutdown
        await graceful_shutdown(tasks)
        logging.info("All tasks stopped successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Monitoring shutdown completed.")
    sys.exit(0)
