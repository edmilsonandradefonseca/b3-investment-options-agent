from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any


class DataProvider(ABC):
    """Provider-independent interface for external market data."""

    name: str

    @abstractmethod
    def get_instruments(self, as_of: datetime) -> list[Any]:
        """Return instruments available at the requested point in time."""
        raise NotImplementedError

    @abstractmethod
    def get_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[Any]:
        """Return normalized market data for a ticker."""
        raise NotImplementedError

    @abstractmethod
    def get_fundamentals(
        self,
        ticker: str,
        as_of: datetime,
    ) -> list[Any]:
        """Return fundamentals available at the requested point in time."""
        raise NotImplementedError

    @abstractmethod
    def get_corporate_actions(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[Any]:
        """Return corporate actions."""
        raise NotImplementedError

    @abstractmethod
    def get_options(
        self,
        ticker: str,
        as_of: datetime,
    ) -> list[Any]:
        """Return option contracts and quotes."""
        raise NotImplementedError

    @abstractmethod
    def get_macro(
        self,
        indicator: str,
        start: date,
        end: date,
    ) -> list[Any]:
        """Return macroeconomic observations."""
        raise NotImplementedError
