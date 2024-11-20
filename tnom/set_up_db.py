"""Initialize and check the database.

It provides a function to initialize and check the database.
"""
from pathlib import Path

import database_handler


def init_and_check_db(working_dir: Path) -> None:
    """Initialize and check the database.

    This function ensures that the necessary database directory and database file
    exist in the specified working directory. If the directory does not exist, it
    is created. If the database file does not exist, it is also created.

    Args:
        working_dir (Path): The path to the working directory where the database
        files should be located.

    Returns:
        None

    """
    if not database_handler.check_if_database_directory_exists():
        database_handler.create_database_directory()
    if not database_handler.check_database_exists(Path(
        working_dir / "chain_database/tnom.db")):
        database_handler.create_database(Path(working_dir / "chain_database/tnom.db"))

