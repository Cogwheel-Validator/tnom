"""A function to collect data from a randomly chosen healthy API."""
from __future__ import annotations

import logging
import random
from typing import Any

import aiohttp
import query
import utility


async def collect_data_from_random_healthy_api(
    healthy_apis: list[str],
    config_yml: dict[str, Any]) -> dict[str, Any] | None:
    """Collects data from a randomly chosen healthy API.

    Args:
        healthy_apis (list[str]): A list of healthy APIs.
        config_yml (dict[str, Any]): The loaded configuration from the YAML file.

    Returns:
        dict[str, Any]: A dictionary containing all the collected data. Returns
        None if no healthy APIs are found.

    """
    if not healthy_apis:
        logging.error("""No healthy APIs found! \n
                      Check your config file or is the chain halted.""")
        # retrun None or an empty list
        return None
    async with aiohttp.ClientSession() as session:
        # select API
        random_healthy_api = (random.choice(healthy_apis))  # noqa: S311
        logging.info(random_healthy_api)

        # collect miss counter
        miss_counter : int = await query.check_miss_counters(
            session, random_healthy_api, config_yml["validator_address"])

        # check aggr prevote resault
        check_for_aggregate_prevotes_result = await query.check_aggregate_pre_vote(
            session, random_healthy_api, config_yml["validator_address"])

        # if everything is ok it should return hash and block height it was sign
        # maybe use this in the future for some kind of statistics?
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

        # collect if the data has been signed
        check_for_aggregate_votes = await query.check_aggregate_vote(
            session, random_healthy_api, config_yml["validator_address"])
        logging.info(check_for_aggregate_votes)
        if check_for_aggregate_votes is True:
            logging.info("Aggregate vote successful")
        elif check_for_aggregate_votes is False:
            # Refine this section later on in case only some pairs are present
            # And if it returns compleatly false
            logging.error("Aggregate vote failed")

        # collect parameters to create the epoch
        collect_slash_window : int = await query.collect_slash_parameters(
            random_healthy_api, session)
        latest_block_result : int = await query.check_latest_block(
            random_healthy_api, session)

        # create epoch
        current_block_height, _ = latest_block_result
        current_epoch : int = utility.create_epoch(current_block_height, collect_slash_window)
        current_epoch : int = utility.create_epoch(
                current_block_height, collect_slash_window)

        wallet_balance : int = await query.check_token_in_wallet(
            random_healthy_api, config_yml.get("price_feed_addr"), session)
        all_data_from_api : dict[str, Any] = {
            "miss_counter": miss_counter,
            "check_for_aggregate_votes": check_for_aggregate_votes,
            "current_epoch": current_epoch,
            "wallet_balance": wallet_balance,
        }
        return all_data_from_api

