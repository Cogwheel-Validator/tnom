"""Functions to querying the Nibiru API for oracle data.

This package has 7 functions:
    - check_aggregate_vote: Check the aggregate vote of a validator.
    - check_aggregate_pre_vote: Check the aggregate pre-vote of a validator.
    - collect_vote_targets: Collect the vote targets from the Nibiru API.
    - collect_slash_parameters: Collect the slash parameters from the Nibiru API.
    - check_token_in_wallet: Check if the price feeder has unibi token in its wallet.
    - check_latest_block: Check the latest block height from the Nibiru API.
    - check_miss_counters: Check the miss counters of a validator.

And 2 classes:
    - AggregatePreVote: Class for aggregate pre-votes.
    - AggregateVoteError: An exception class for errors related to aggregate votes.

Usage:
    Used to query the Nibiru API for oracle data.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from http import HTTPStatus

import aiohttp

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

CODE_ERROR = 2

@dataclass
class AggregatePreVote:
    """Class for aggregate votes.

    Attributes:
        hash: The hash of the aggregate vote.
        submit_block: The block height when the aggregate vote was submitted.

    """

    hash: str
    submit_block: int

@dataclass
class AggregateVoteError(Exception):
    """An exception class for errors related to aggregate votes.

    Attributes:
        message (str): A human-readable error message.
        code (int): An error code.

    """

    message: str
    code: int

    def __str__(self) -> str:
        """Returns a human-readable string representation of the AggregateVoteError."""
        return f"AggregateVoteError (code {self.code}): {self.message}"

async def check_miss_counters(
    session: aiohttp.ClientSession,
    api: str,
    validator_address: str,
) -> int | None:
    """Check the miss counter for validator's oracle voting.

    Args:
        session: The aiohttp client session.
        api: The API URL to query.
        validator_address: The address of the validator to query.

    Returns:
        The miss counter of the validator if successful, otherwise None.

    """
    async with session.get(
        f"{api}/nibiru/oracle/v1beta1/validators/{validator_address}/miss",
    ) as response:
        if response.status == HTTPStatus.OK:
            logger.info("Collecting miss counter")
            logger.debug((await response.json())["miss_counter"])
            return (await response.json())["miss_counter"]
        logger.error("Failed to collect miss counter")
        return None

async def collect_vote_targets(
    session: aiohttp.ClientSession,
    api: str,
) -> list[str] | None:
    """Collect the vote targets of a validator.

    Args:
        session: The aiohttp client session.
        api: The API URL to query.

    Returns:
        The list of vote targets if successful, otherwise None.

    """
    async with session.get(
        f"{api}/nibiru/oracle/v1beta1/pairs/vote_targets",
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        if response.status == HTTPStatus.OK:
            logger.info("Collecting vote targets")
            logger.debug((await response.json())["vote_targets"])
            return (await response.json())["vote_targets"]
        logger.error("Failed to collect vote targets")
        return None

async def check_aggregate_pre_vote(
    session: aiohttp.ClientSession,
    api: str,
    validator_address: str,
) -> AggregatePreVote | str | None:
    """Check the aggregate vote of a validator.

    Args:
        session: The aiohttp client session.
        api: The API URL to query.
        validator_address: The address of the validator to query.

    Returns:
        An AggregateVote object if successful, otherwise a string indicating the error.

    """
    async with session.get(
        f"{api}/nibiru/oracle/v1beta1/validators/{validator_address}/aggregate_prevote",
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        if response.status == HTTPStatus.OK:
            data = await response.json(content_type="application/json")
            if data["code"] == CODE_ERROR:
                logger.error(data["message"])
                raise AggregateVoteError(data["message"], data["code"])
            if "aggregate_prevote" in data:
                logger.info("Collecting aggregate prevote")
                return AggregatePreVote(
                    hash=data["aggregate_prevote"].get("hash"),
                    submit_block=data["aggregate_prevote"].get("submit_block"),
                )
        logger.error("Failed to collect aggregate prevote")
        return None
async def check_aggregate_vote(
    session: aiohttp.ClientSession,
    api: str,
    validator_address: str,
) -> str | None | AggregateVoteError:
    """Check the aggregate vote of a validator.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session.
        api (str): The API URL to query.
        validator_address (str): The address of the validator to query.

    Returns:
        str | None | AggregateVoteError:
        An AggregateVote object if successful, otherwise a string indicating the error.

    """
    async with session.get(
    # Miss type on the API URL here make sure it is "valdiators" instead of "validators"
    # Probably a miss type when API route was made
        f"{api}/nibiru/oracle/v1beta1/valdiators/{validator_address}/aggregate_vote",
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        voting_targets = await collect_vote_targets(session, api)
        if response.status == HTTPStatus.OK:
            data = await response.json(content_type="application/json")
            if data["code"] == CODE_ERROR:
                raise AggregateVoteError(data["message"], data["code"])
            if "aggregate_vote" in data:
                exchange_rates = data["aggregate_vote"].get("exchange_rate_tuples", [])
                for exchange_rate in exchange_rates:
                    pair = exchange_rate.get("pair")
                    logging.debug(pair)
                    if pair is not None and pair not in voting_targets:
                        raise AggregateVoteError(
                            message=f"{pair} not in voting targets", code=CODE_ERROR,
                        )
                # If we reach this point, all pairs are present, so return "OK"
                return "OK"
            logging.error("Failed to collect aggregate vote")
            return None
        logging.error("Failed to collect aggregate vote")
        return None

async def collect_slash_parameters(
    api: str,
    session: aiohttp.ClientSession,
) -> int | None:
    """Collect the slash parameters for the oracle voting.

    Args:
        api (str): The API URL
        session (aiohttp.ClientSession): The aiohttp client session

    Returns:
        int | None: The slash window if successful, otherwise None

    """
    async with session.get(
        f"{api}/nibiru/oracle/v1beta1/params",
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        if response.status == HTTPStatus.OK:
            json_data = await response.json(content_type="application/json")
            logging.info("Collecting slash parameters")
            logging.debug(json_data.get("params", {}).get("slash_window"))
            return json_data.get("params", {}).get("slash_window")
        logging.error("Failed to collect slash parameters")
        return None

async def check_token_in_wallet(
    api: str,
    price_feeder_address: str,
    session: aiohttp.ClientSession,
) -> int | None:
    """Check if the price feeder has the specified token in its wallet.

    Args:
        api (str): The API URL
        price_feeder_address (str): The address of the price feeder wallet
        session (aiohttp.ClientSession): The aiohttp client session

    Returns:
        int | None: The amount of unibi tokens in the wallet if successful,
        otherwise None

    """
    async with session.get(
        f"{api}/cosmos/bank/v1beta1/spendable_balances/{price_feeder_address}",
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        if response.status == HTTPStatus.OK:
            json_data = await response.json(content_type="application/json")
            balances = json_data.get("result", [])
            logging.info("Collecting token balance")
            for balance in balances:
                if balance["denom"] == "unibi":
                    return int(balance["amount"])
            logging.error("Failed to collect token balance")
            return None
        logging.error("Failed to collect token balance")
        return None

async def check_latest_block(
    api: str,
    session: aiohttp.ClientSession,
) -> tuple[int, str] | None:
    """Check the latest block height of the chain.

    Args:
        api (str): The API URL
        session (aiohttp.ClientSession): The aiohttp client session

    Returns:
        tuple[int, str] | None: A tuple of the latest block height and timestamp
        if successful, otherwise None

    """
    try:
        async with session.get(
            f"{api}/cosmos/base/tendermint/v1beta1/blocks/latest",
            timeout=aiohttp.ClientTimeout(total=5),
        ) as response:
            if response.status == HTTPStatus.OK:
                json_data = await response.json(content_type="application/json")
                block_height = int(json_data["block"]["header"]["height"])
                timestamp = json_data["block"]["header"]["time"]
                return (block_height, timestamp)
            logging.error("Failed to collect latest block %s", response.status)
            return None
    except aiohttp.ContentTypeError as e:
        logging.exception("Failed to collect latest block", exc_info=e)
        return None