import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import alerts
import config_load
import database_handler
import query_rand_api
from check_apis import check_apis
from set_up_db import init_and_check_db

ONE_NIBIRU = 1000000
ZERO_PT_ONE = 100000

async def main():
    # Define args
    working_dir: Path = Path.cwd()
    config_path: Path = working_dir / "config.yml"
    alert_path: Path = working_dir / "alert.yml"
    database_path: Path = working_dir / "chain_database"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--working_dir",
        type=str,
        help="""The working directory where the config and alert YAML
        files are located and where the database is initialized and checked.

        Example: --working_dir /home/user/tnom""",
        default=working_dir,
        required=False,
    )
    parser.add_argument(
        "--config_path",
        type=str,
        help="""The path to the config YAML file

        Example: --config_path /home/user/tnom/config.yml""",
        default=config_path,
        required=False,
    )
    parser.add_argument(
        "--alert_path",
        type=str,
        help="""The path to the alert YAML file

        Example: --alert_path /home/user/tnom/alert.yml""",
        required=False,
        default=alert_path,
    )
    args = parser.parse_args()
    if args.working_dir:
        working_dir = Path(args.working_dir)

    # Step one - Initialize and check the database
    init_and_check_db(working_dir)

    # Step two - Load the config and alert YAML files
    config_yml = config_load.load_config_yml(args.config_path)
    alert_yml = config_load.load_alert_yml(args.alert_path)

    # Step three - check APIs
    # Should repeat from here
    healthy_apis = await check_apis(config_yml)

    # Step four - Make query with random healthy API
    query_resaults = await query_rand_api.collect_data_from_random_healthy_api(
        healthy_apis, config_yml)
    # Extract data here
    query_data : dict = {
        "miss_counter" : query_resaults["miss_counter"],
        "check_for_aggregate_votes" : query_resaults["check_for_aggregate_votes"],
        "current_epoch" : query_resaults["current_epoch"],
        "wallet_balance" : query_resaults["wallet_balance"],
        }
    # Step five - Write data to database
    # Step 5.1 - Check if the current_epoch exists in the database
    if database_handler.check_if_epoch_is_recorded(
        database_path, query_data["current_epoch"]):
        # Step 5.2a - Update tthe existing db with data

        # read current epoch data
        read_crw_data: dict = database_handler.read_current_epoch_data(
            database_path, query_data["current_epoch"])
        db_unsigned_or_ev: int = read_crw_data["unsigned_oracle_events"]
        db_small_bal_alert: int = read_crw_data["small_balance_alert_executed"]
        db_very_small_bal_alert: int = read_crw_data["very_small_balance_alert_executed"]
        # if the check failed the return should be false adding +1 to not signing events
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
        # Step 5.2b if no db, no current epoch entered or just starting for first time
        # make the new entry in the db

        # check if there is a previous entry
        if database_handler.check_if_epoch_is_recorded(
        database_path, query_data["current_epoch"] - 1):
            read_prev_crw_data : dict = database_handler.read_current_epoch_data(
                database_path, query_data["current_epoch"] - 1)
            if read_prev_crw_data["slash_epoch"] == query_data["current_epoch"] - 1:
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
    # Step 6 alerting system
    # Step 6.1 check current alerts
    alert_yml = config_load.load_alert_yml(args.alert_path)
    telegram_enabled : bool = alert_yml["telegram_alerts"]
    pagerduty_enabled : bool = alert_yml["pagerduty_alerts"]
    if telegram_enabled is False and pagerduty_enabled is False:
        logging.error("""No alerts are enabled! Please enable at least one alert.
                      Please check the alert YAML file. Kill the script...""")
        sys.exit()
    read_crw_data: dict = database_handler.read_current_epoch_data(
            database_path, query_data["current_epoch"])
    db_small_bal_alert: int = read_crw_data["small_balance_alert_executed"]
    db_very_small_bal_alert: int = read_crw_data["very_small_balance_alert_executed"]

    # Step 6.2 trigger alerts
    # alert is balance has less then 1 NIBI
    if query_data["wallet_balance"] < ONE_NIBIRU and db_small_bal_alert == 0:
        db_small_bal_alert += 1
        database_handler.overwrite_single_field(
            database_path, query_data["current_epoch"],
            "small_balance_alert_executed", db_small_bal_alert)
        alert_details: dict[str, Any] = {
            "wallet_balance": (str(query_data["wallet_balance"]),"unibi"),
            "alert_level": "high",
        }
        summary: str = "Price feeder wallet balance has less than 1 NIBI!"
        severity: str = "high"
        if pagerduty_enabled is True:
            alerts.pagerduty_alert_trigger(alert_yml["routing_key"],alert_details,summary,severity)
        if telegram_enabled is True:
            alerts.telegram_alert_trigger(alert_yml["telegram_bot_token"],alert_details,alert_yml["telegram_chat_id"])
    # alert if balance has less then 0.1 NIBI
    if query_data["wallet_balance"] < ZERO_PT_ONE and db_very_small_bal_alert == 0:
        db_very_small_bal_alert += 1
        database_handler.overwrite_single_field(
            database_path, query_data["current_epoch"],
            "very_small_balance_alert_executed", db_very_small_bal_alert)
        alert_details: dict[str, Any] = {
            "wallet_balance": (str(query_data["wallet_balance"]),"unibi"),
            "alert_level": "critical",
        }
        summary: str = "Price feeder wallet balance has less than 0.1 NIBI!"
        severity: str = "critical"
        if pagerduty_enabled is True:
            alerts.pagerduty_alert_trigger(alert_yml["routing_key"],alert_details,summary,severity)
        if telegram_enabled is True:
            alerts.telegram_alert_trigger(alert_yml["telegram_bot_token"],alert_details,alert_yml["telegram_chat_id"])
    # return alert confirmation that balance is within healthy balance
    if query_data["wallet_balance"] >= ONE_NIBIRU and db_small_bal_alert != 0:
        db_small_bal_alert = 0
        database_handler.overwrite_single_field(
            database_path, query_data["current_epoch"],
            "small_balance_alert_executed", db_small_bal_alert)
        alert_details: dict[str, Any] = {
            "wallet_balance": (str(query_data["wallet_balance"]),"unibi"),
            "alert_level": "info",
        }
        summary: str = "Price feeder wallet balance has more than 1 NIBI!"
        severity: str = "info"
        if pagerduty_enabled is True:
            alerts.pagerduty_alert_trigger(alert_yml["routing_key"],alert_details,summary,severity)
        if telegram_enabled is True:
            alerts.telegram_alert_trigger(alert_yml["telegram_bot_token"],alert_details,alert_yml["telegram_chat_id"])
    # return alert confirmation that balance is within healthy balance
    if query_data["wallet_balance"] >= ZERO_PT_ONE and db_very_small_bal_alert != 0:
        db_very_small_bal_alert = 0
        database_handler.overwrite_single_field(
            database_path, query_data["current_epoch"],
            "very_small_balance_alert_executed", db_very_small_bal_alert)
        alert_details: dict[str, Any] = {
            "wallet_balance": (str(query_data["wallet_balance"]),"unibi"),
            "alert_level": "info",
        }
        summary: str = "Price feeder wallet balance has more than 0.1 NIBI!"
        severity: str = "info"
        if pagerduty_enabled is True:
            alerts.pagerduty_alert_trigger(alert_yml["routing_key"],alert_details,summary,severity)
        if telegram_enabled is True:
            alerts.telegram_alert_trigger(alert_yml["telegram_bot_token"],alert_details,alert_yml["telegram_chat_id"])
