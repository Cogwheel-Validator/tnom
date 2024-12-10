"""The database_handler package.

It provides the following functions:
    - check_if_database_directory_exists: Check if the database directory exists.
    - check_database_exists: Check if the database file exists.
    - create_database: Create the database file.
    - create_database_directory: Create the database directory.
    - read_current_epoch_data: Read the current epoch data from the database.
    - write_epoch_data: Write the current epoch data to the database.
    - overwrite_single_field: Overwrite a single field in the database.

Usage:
    The database_handler package provides functions for interacting with the database.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path


def check_if_database_directory_exists() -> bool:
    """Check if the database directory exists."""
    return Path("chain_database").exists()

def check_database_exists(path: Path) -> bool:
    """Check if the database file exists.

    Args:
        path (Path): The path to the database file to check.

    Returns:
        bool: True if the database file exists, False otherwise.

    """
    return Path(path).exists()

def check_and_update_database_schema(path: Path) -> None:
    """Check if all expected columns exist in the database table.

    Add any missing columns to ensure compatibility with newer versions.

    Args:
        path (Path): The path to the database file.

    Returns:
        None

    """
    # Define the expected columns with their default values and data types
    # This makes it easy to add new columns in the future
    expected_columns = {
        "slash_epoch": "INTEGER PRIMARY KEY",
        "miss_counter_events": "INTEGER",
        "miss_counter_p1_executed": "INTEGER DEFAULT 0",
        "miss_counter_p2_executed": "INTEGER DEFAULT 0",
        "miss_counter_p3_executed": "INTEGER DEFAULT 0",
        "unsigned_oracle_events": "INTEGER",
        "price_feed_addr_balance": "INTEGER",
        "small_balance_alert_executed": "INTEGER",
        "very_small_balance_alert_executed": "INTEGER",
        "consecutive_misses": "INTEGER DEFAULT 0",
        "api_cons_miss": "INTEGER DEFAULT 0",
    }

    try:
        with sqlite3.connect(path) as conn:
            # Get existing columns
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(tnom)")
            existing_columns = {column[1] for column in cur.fetchall()}

            # Check for missing columns and add them
            for column_name, column_type in expected_columns.items():
                if column_name not in existing_columns:
                    try:
                        # Add the missing column
                        cur.execute(
                            f"ALTER TABLE tnom ADD COLUMN {column_name} {column_type}")
                        logging.info("Added missing column: %s", column_name)
                    except sqlite3.Error as e:
                        logging.exception("Error adding column %s: %s", column_name, e)  # noqa: TRY401

            # Commit the changes
            conn.commit()

    except sqlite3.Error as e:
        logging.exception("Database schema update failed: %s", e)  # noqa: TRY401
        raise

def read_last_recorded_epoch(path: Path) -> int:
    """Read the most recent epoch from the database.

    Args:
        path (Path): The path to the database file.

    Returns:
        int: The most recent epoch recorded in the database.

    Raises:
        ValueError: If no epochs are found in the database.

    """
    try:
        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(slash_epoch) FROM tnom")
            result = cur.fetchone()[0]

            if result is None:
                raise ValueError("No epochs found in the database")

            return result
    except sqlite3.Error as e:
        logging.exception("Error reading last epoch: %s", e)
        raise


def create_database(path: Path) -> None:
    """Create the database file.

    Args:
        path (Path): The path to the database file to create.

    Returns:
        None

    """
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS tnom (
                slash_epoch INTEGER PRIMARY KEY,
                miss_counter_events INTEGER,
                miss_counter_p1_executed INTEGER DEFAULT 0,
                miss_counter_p2_executed INTEGER DEFAULT 0,
                miss_counter_p3_executed INTEGER DEFAULT 0,
                unsigned_oracle_events INTEGER,
                price_feed_addr_balance INTEGER,
                small_balance_alert_executed INTEGER,
                very_small_balance_alert_executed INTEGER,
                consecutive_misses INTEGER DEFAULT 0,
                api_cons_miss INTEGER DEFAULT 0
            )""",
        )

def create_database_directory() -> None:
    """Create the database directory."""
    Path("chain_database").mkdir(parents=True, exist_ok=True)

def check_if_epoch_is_recorded(path: Path, epoch: int) -> bool:
    """Check if data exists for the given epoch.

    Args:
        path (Path): The path to the database file.
        epoch (int): The epoch to check.

    Returns:
        bool: True if epoch data exists, False otherwise.

    """
    try:
        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM tnom WHERE slash_epoch = ?", (epoch,))
            return cur.fetchone() is not None
    except sqlite3.Error:
        return False

def read_current_epoch_data(path: Path, epoch: int) -> dict[str, int]:
    """Read the current epoch data from the database.

    Args:
        path (Path): The path to the database file.
        epoch (int): The epoch to read.

    Returns:
        dict[str, int]: A dictionary containing the current epoch data.

    Raises:
        ValueError: If no data is found in the database.

    """
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM tnom WHERE slash_epoch = ?", (epoch,))
        data = cur.fetchone()
        if data is None:
            msg = "No data found in database"
            raise ValueError(msg)
        return {
            "slash_epoch": data["slash_epoch"],
            "miss_counter_events": data["miss_counter_events"],
            "miss_counter_p1_executed": data["miss_counter_p1_executed"],
            "miss_counter_p2_executed": data["miss_counter_p2_executed"],
            "miss_counter_p3_executed": data["miss_counter_p3_executed"],
            "unsigned_oracle_events": data["unsigned_oracle_events"],
            "price_feed_addr_balance": data["price_feed_addr_balance"],
            "small_balance_alert_executed": data["small_balance_alert_executed"],
            "very_small_balance_alert_executed": data[
                "very_small_balance_alert_executed"],
            "consecutive_misses": data["consecutive_misses"],
            "api_cons_miss": data["api_cons_miss"],
        }

def write_epoch_data(path: Path, data: dict[str, int]) -> None:
    """Write or update the current epoch data to the database.

    If the epoch already exists, it will update all fields with new values.

    Args:
        path (Path): The path to the database file.
        data (dict[str, int]): A dictionary containing the current epoch data.

    Returns:
        None

    Raises:
        TypeError: If any of the given data contains a null value.
        ValueError: If any of the given data contains an invalid value.
        sqlite3.Error: If any database operation fails.

    """
    if path is None or not isinstance(path, Path):
        msg = "path must be a Path object"
        raise TypeError(msg)
    if data is None or not isinstance(data, dict):
        msg = "data must be a dictionary"
        raise TypeError(msg)
    if (
        data.get("slash_epoch") is None
        or data.get("miss_counter_events") is None
        or data.get("miss_counter_p1_executed") is None
        or data.get("miss_counter_p2_executed") is None
        or data.get("miss_counter_p3_executed") is None
        or data.get("unsigned_oracle_events") is None
        or data.get("price_feed_addr_balance") is None
        or data.get("small_balance_alert_executed") is None
        or data.get("very_small_balance_alert_executed") is None
        or data.get("consecutive_misses") is None
        or data.get("api_cons_miss") is None
    ):
        msg = "data must contain all required fields"
        raise ValueError(msg)
    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        # Try to insert first
        try:
            cur.execute(
                "INSERT INTO tnom VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    data["slash_epoch"],
                    data["miss_counter_events"],
                    data["miss_counter_p1_executed"],
                    data["miss_counter_p2_executed"],
                    data["miss_counter_p3_executed"],
                    data["unsigned_oracle_events"],
                    data["price_feed_addr_balance"],
                    data["small_balance_alert_executed"],
                    data["very_small_balance_alert_executed"],
                    data["consecutive_misses"],
                    data["api_cons_miss"],
                ),
            )

        except sqlite3.IntegrityError:
            # If insert fails due to existing epoch, update all fields
            cur.execute("""
                UPDATE tnom
                SET miss_counter_events = ?,
                    miss_counter_p1_executed = ?,
                    miss_counter_p2_executed = ?,
                    miss_counter_p3_executed = ?,
                    unsigned_oracle_events = ?,
                    price_feed_addr_balance = ?,
                    small_balance_alert_executed = ?,
                    very_small_balance_alert_executed = ?,
                    consecutive_misses = ?,
                    api_cons_miss = ?
                WHERE slash_epoch = ?
            """, (
                data["miss_counter_events"],
                data["miss_counter_p1_executed"],
                data["miss_counter_p2_executed"],
                data["miss_counter_p3_executed"],
                data["unsigned_oracle_events"],
                data["price_feed_addr_balance"],
                data["small_balance_alert_executed"],
                data["very_small_balance_alert_executed"],
                data["consecutive_misses"],
                data["slash_epoch"],
                data["api_cons_miss"],
            ))
        conn.commit()

def overwrite_single_field(path: Path, epoch: int, field: str, value: int) -> None:
    """Overwrites a single field in the database.

    Args:
        path (Path): The path to the database file.
        epoch (int): The epoch to overwrite.
        field (str): The name of the field to overwrite.
        value (int): The new value for the field.

    Returns:
        None

    Raises:
        TypeError: If any of the given data contains a null value.
        ValueError: If any of the given data contains an invalid value.
        sqlite3.Error: If any database operation fails.

    """
    if not isinstance(path, Path):
        msg = "path must be a Path object"
        raise TypeError(msg)
    if field is None or not isinstance(field, str):
        msg = "field must be a string"
        raise TypeError(msg)
    if value is None or not isinstance(value, int):
        msg = "value must be an integer"
        raise TypeError(msg)

    allowed_columns = [
        "miss_counter_events",
        "miss_counter_p1_executed",
        "miss_counter_p2_executed",
        "miss_counter_p3_executed",
        "unsigned_oracle_events",
        "price_feed_addr_balance",
        "small_balance_alert_executed",
        "very_small_balance_alert_executed",
        "consecutive_misses",
        "api_cons_miss",
    ]

    if field not in allowed_columns:
        msg = f"""Invalid column name: {field}.
        Allowed columns: {allowed_columns}"""
        raise ValueError(msg)

    try:
        with sqlite3.connect(path) as conn:
            cur = conn.cursor()
            query = f"UPDATE tnom SET {field} = ? WHERE slash_epoch = ?" # TO DO
            # fix this error although it should still be protected by allowed columns
            cur.execute(query, (value, epoch))
            conn.commit()
    except sqlite3.Error as e:
        msg = "Database operation failed"
        raise sqlite3.Error(msg) from e


