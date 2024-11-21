"""A function to collect data from a randomly chosen healthy API."""
from __future__ import annotations

import logging
import random
from typing import Any

import aiohttp
import query
import utility

ONE_NIBIRU = 1000000
ZERO_POINT_ONE_NIBIRU = 100000
async def collect_data_from_random_healthy_api(
    healthy_apis: list[str],
    config_yml: dict[str, Any]) -> dict[str, Any]:
    """Collects data from a randomly chosen healthy API.

    Args:
        healthy_apis (list[str]): A list of healthy APIs.
        config_yml (dict[str, Any]): The loaded configuration from the YAML file.

    Returns:
        dict[str, Any]: A dictionary containing all the collected data.

    """
    async with aiohttp.ClientSession() as session:
        # select API
        random_healthy_api : str = (random.choice(healthy_apis)).get("api")  # noqa: S311
        # collect miss counter
        miss_counter : int = await query.check_miss_counters(
            session, random_healthy_api, config_yml["validator_address"])
        # check aggr prevote resault
        check_for_aggregate_prevotes_result = await query.check_aggregate_pre_vote(
            session, random_healthy_api, config_yml["validator_address"])
        if isinstance(check_for_aggregate_prevotes_result, query.AggregatePreVote):
            # Everything is OK, use the AggregatePreVote data
            prv_hash = check_for_aggregate_prevotes_result.hash
            submit_block = check_for_aggregate_prevotes_result.submit_block
            logging.info("Aggregate pre-vote successful")
            logging.debug(prv_hash, "\n", submit_block)
        elif isinstance(check_for_aggregate_prevotes_result, query.AggregateVoteError):
            # Handle the error
            error_message = check_for_aggregate_prevotes_result.message
            error_code = check_for_aggregate_prevotes_result.code
            logging.error(error_message, "\n", error_code)
        elif check_for_aggregate_prevotes_result is None:
            error_message = "An error occurred while checking aggregate prevote"
            logging.error(error_message)
            # TO DO make sure to add proper error handling in this case and instructions
        check_for_aggregate_votes = await query.check_aggregate_vote(
            session, random_healthy_api, config_yml["validator_address"])
        if check_for_aggregate_votes is True:
            logging.info("Aggregate vote successful")
        elif check_for_aggregate_votes is False:
            # Refine this section later on in case only some pairs are present
            # And if it returns compleatly false
            logging.error("Aggregate vote failed")
        collect_slash_window : int = await query.collect_slash_parameters(
            session, random_healthy_api)
        current_block_height : int = await query.check_latest_block(
            session, random_healthy_api)[0]
        current_epoch : int = await utility.create_epoch(
            current_block_height, collect_slash_window,
        )
        wallet_balance : int = await query.check_token_in_wallet(
            session, random_healthy_api, config_yml["price_feeder_address"])
        if wallet_balance > ONE_NIBIRU:
            wallet_balance_healthy : bool = True
            critical_level_reached : bool = False
        elif wallet_balance <= ONE_NIBIRU and wallet_balance > ZERO_POINT_ONE_NIBIRU:
            wallet_balance_healthy : bool = False
            critical_level_reached : bool = False
        elif wallet_balance <= ZERO_POINT_ONE_NIBIRU:
            wallet_balance_healthy : bool = False
            critical_level_reached : bool = True
        all_data_from_api : dict[str, Any] = {
            "miss_counter": miss_counter,
            "check_for_aggregate_votes": check_for_aggregate_votes,
            "current_epoch": current_epoch,
            "wallet_balance": wallet_balance,
            "wallet_balance_healthy": wallet_balance_healthy,
            "critical_level_reached": critical_level_reached,
        }
        return all_data_from_api

