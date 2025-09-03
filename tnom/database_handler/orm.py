"""Database ORM models and handler for SQLAlchemy operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import sqlalchemy
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

if TYPE_CHECKING:
    import types
    from pathlib import Path


class SqlLiteDB:
    """SQL lite database handler for any ORM operations."""

    def __init__(self, db_path: Path) -> None:
        """Initialize the SqlLiteDB class.

        Args:
            db_path (Path): The path to the database file.

        """
        self.db = sqlalchemy.create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.db)

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name (str): Name of the table to check

        Returns:
            bool: True if table exists, False otherwise

        """
        inspector = inspect(self.db)
        return table_name in inspector.get_table_names()

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class ChainState(Base):
    """SQLAlchemy model for the chain state."""

    __tablename__: str = "chain_state"

    chain_name: Mapped[str] = mapped_column(sqlalchemy.Text, primary_key=True)
    epoch: Mapped[int | None]  # epoch doesn't exist for the symphony at the moment
    miss_counter_events: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    miss_counter_p1: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    miss_counter_p2: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    miss_counter_p3: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    unsigned_oracle_events: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    small_balance_alert: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    very_small_balance_alert: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    consecutive_misses: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
    api_cons_miss: Mapped[int] = mapped_column(sqlalchemy.Integer, default=0)
