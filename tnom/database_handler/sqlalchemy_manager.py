"""SQLAlchemy-based database manager to replace sqlite3 operations.

This module provides SQLAlchemy equivalents for all the functions in db_manager.py
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from tnom.database_handler.orm import Base, ChainState, SqlLiteDB


class SqlSetup:
    """SQLAlchemy setup for the database."""

    def __init__(self, path: Path) -> None:
        """Initialize the SqlSetup class.

        Args:
            path (Path): The path to the database file.

        """
        self.path = path

    def check_if_database_directory_exists() -> bool:
        """Check if the database directory exists."""
        return Path("chain_database").exists()

    def check_database_exists(self) -> bool:
        """Check if the database file exists.

        Args:
            self.path (Path): The path to the database file.

        Returns:
            bool: True if the database file exists, False otherwise.

        """
        return Path(self.path).exists()

    def create_database_directory(self, db_dir: Path) -> None:
        """Create the database directory."""
        db_dir.mkdir(parents=True, exist_ok=True)

    def check_and_update_database_schema(self) -> None:
        """Check if all expected columns exist in the database table.

        Add any missing columns to ensure compatibility with newer versions.

        Args:
            self.path (Path): The path to the database file.

        Returns:
            None

        """
        with SqlLiteDB(self.path) as db:
            Base.metadata.create_all(db.db)

    def table_exists(self, table_name: str) -> bool:
        """Check if a specific table exists in the database.

        Args:
            self.path (Path): The path to the database file.
            table_name (str): Name of the table to check.

        Returns:
            bool: True if table exists, False otherwise.

        """
        with SqlLiteDB(self.path) as db:
            return db.table_exists(table_name)


class SqlManager:
    """SQLAlchemy manager for the database.

    This class should be used for multiple chains and each chain should have it's
    own instance of the class.
    """

    def __init__(self, path: Path, chain_name: str, logger: logging.Logger) -> None:
        """Initialize the SqlManager class.

        Args:
            path (Path): The path to the database file.
            chain_name (str): The name of the chain.

        """
        self.path = path
        self.chain_name = chain_name
        self.logger = logger

    def read_last_recorded_epoch(self) -> int:
        """Read the most recent epoch from the database using SQLAlchemy.

        Args:
            path (Path): The path to the database file.

        Returns:
            int: The most recent epoch recorded in the database.

        Raises:
            ValueError: If no epochs are found in the database.

        """
        if self.chain_name != "nibiru":
            msg = "This function is only supported for nibiru at the moment"
            raise ValueError(msg)

        try:
            with SqlLiteDB(self.path).get_session() as session:
                result = session.query(func.max(ChainState.epoch)).scalar()

                if result is None:
                    msg = "No epochs found in the database"
                    raise ValueError(msg)

                return result
        except SQLAlchemyError as e:
            self.logger.exception("Error reading last epoch: %s", e)
            raise


    def check_if_epoch_is_recorded(self, epoch: int) -> bool:
        """Check if data exists for the given epoch using SQLAlchemy.

        Args:
            path (Path): The path to the database file.
            epoch (int): The epoch to check.

        Returns:
            bool: True if epoch data exists, False otherwise.

        """
        try:
            with SqlLiteDB(self.path).get_session() as session:
                result = session.query(ChainState).filter_by(epoch=epoch).first()
                return result is not None
        except SQLAlchemyError:
            return False


    def read_current_epoch_data(self, epoch: int) -> ChainState:
        """Read the current epoch data from the database using SQLAlchemy.

        Args:
            path (Path): The path to the database file.
            epoch (int): The epoch to read.

        Returns:
            ChainState: A ChainState object containing the current epoch data.

        Raises:
            ValueError: If no data is found in the database.
        """
        with SqlLiteDB(self.path).get_session() as session:
            data = session.query(ChainState).filter_by(epoch=epoch).first()

            if data is None:
                msg = "No data found in database"
                raise ValueError(msg)

            return data


    def write_epoch_data(self, data: ChainState) -> None:
        """Write or update the current epoch data to the database using SQLAlchemy.

        If the epoch already exists, it will update all fields with new values.

        Args:
            data (ChainState): A ChainState object containing the current epoch data.

        Returns:
            None

        Raises:
            TypeError: If any of the given data contains a null value.
            ValueError: If any of the given data contains an invalid value.
            SQLAlchemyError: If any database operation fails.
        """
        if data is None or not isinstance(data, ChainState):
            msg = "data must be a ChainState object"
            raise TypeError(msg)
        if data is None or not isinstance(data, dict):
            msg = "data must be a dictionary"
            raise TypeError(msg)

        required_fields = [
            "epoch",
            "miss_counter_events",
            "miss_counter_p1",
            "miss_counter_p2",
            "miss_counter_p3",
            "unsigned_oracle_events",
            "small_balance_alert",
            "very_small_balance_alert",
            "consecutive_misses",
            "api_cons_miss",
            "chain_name",
        ]

        for field in required_fields:
            if data.get(field) is None:
                msg = f"data must contain all required fields. Missing: {field}"
                raise ValueError(msg)

        try:
            with SqlLiteDB(self.path).get_session() as session:
                # Check if the record already exists
                existing_record = (
                    session.query(ChainState)
                    .filter_by(epoch=data.epoch)
                    .first()
                )

                if existing_record:
                    # Update existing record
                    for field in required_fields:
                        if field != "slash_epoch":  # Don't update primary key
                            setattr(existing_record, field, data[field])
                else:
                    # Create new record
                    new_record = ChainState(**data)
                    session.add(new_record)

                session.commit()

        except SQLAlchemyError as e:
            self.logger.exception("Database operation failed: %s", e)
            raise


    def overwrite_single_field(self, epoch: int, field: str, value: int) -> None:
        """Overwrites a single field in the database using SQLAlchemy.

        Args:
            self.path (Path): The path to the database file.
            epoch (int): The epoch to overwrite.
            field (str): The name of the field to overwrite.
            value (int): The new value for the field.

        Returns:
            None

        Raises:
            TypeError: If any of the given data contains a null value.
            ValueError: If any of the given data contains an invalid value.
            SQLAlchemyError: If any database operation fails.
        """
        if not isinstance(self.path, Path):
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
            msg = f"Invalid column name: {field}. Allowed columns: {allowed_columns}"
            raise ValueError(msg)

        try:
            with SqlLiteDB(self.path).get_session() as session:
                record = session.query(ChainState).filter_by(slash_epoch=epoch).first()

                if record is None:
                    msg = f"No record found for epoch: {epoch}"
                    raise ValueError(msg)

                setattr(record, field, value)
                session.commit()

        except SQLAlchemyError as e:
            msg = f"Database operation failed: {e}"
            raise SQLAlchemyError(msg) from e


    # Additional helper functions for common SQLAlchemy patterns


    def get_all_epochs(self) -> list[int]:
        """Get all epochs from the database.

        Args:
            self.path (Path): The path to the database file.

        Returns:
            list[int]: List of all epochs in the database.
        """
        with SqlLiteDB(self.path).get_session() as session:
                epochs = (
                    session.query(ChainState.epoch)
                    .order_by(ChainState.epoch)
                    .all()
                )
                return [epoch[0] for epoch in epochs]


    def get_records_by_criteria(
        self,
        min_epoch: Optional[int] = None,
        max_epoch: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> list[ChainState]:
        """Get records based on criteria.

        Args:
            self.path (Path): The path to the database file.
            min_epoch (Optional[int]): Minimum epoch to include.
            max_epoch (Optional[int]): Maximum epoch to include.
            limit (Optional[int]): Maximum number of records to return.

        Returns:
            list[ChainState]: List of matching records.
        """
        with SqlLiteDB(self.path).get_session() as session:
                query = session.query(ChainState)

                if min_epoch is not None:
                    query = query.filter(ChainState.epoch >= min_epoch)
                if max_epoch is not None:
                    query = query.filter(ChainState.epoch <= max_epoch)

                query = query.order_by(ChainState.epoch)

                if limit is not None:
                    query = query.limit(limit)

                return query.all()


    def delete_epoch_data(self, epoch: int) -> bool:
        """Delete data for a specific epoch.

        Args:
            self.path (Path): The path to the database file.
            epoch (int): The epoch to delete.

        Returns:
            bool: True if a record was deleted, False if no record existed.
        """
        try:
            with SqlLiteDB(self.path).get_session() as session:
                    record = session.query(ChainState).filter_by(epoch=epoch).first()

                    if record is None:
                        return False

                    session.delete(record)
                    session.commit()
                    return True

        except SQLAlchemyError as e:
            self.logger.exception("Error deleting epoch data: %s", e)
            raise

