"""The database_handler package.

The database_handler package provides functions for interacting with the database.
"""
from .db_manager import (
    check_and_update_database_schema,
    check_database_exists,
    check_if_database_directory_exists,
    check_if_epoch_is_recorded,
    create_database,
    create_database_directory,
    overwrite_single_field,
    read_current_epoch_data,
    read_last_recorded_epoch,
    write_epoch_data,
)

__all__ = [
    "check_and_update_database_schema",
    "check_database_exists",
    "check_if_database_directory_exists",
    "check_if_epoch_is_recorded",
    "create_database",
    "create_database_directory",
    "overwrite_single_field",
    "read_current_epoch_data",
    "read_last_recorded_epoch",
    "write_epoch_data",
]
