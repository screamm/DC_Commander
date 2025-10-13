"""Strategy pattern implementation for Modern Commander.

Provides flexible sorting strategies for file listings.
"""

from abc import ABC, abstractmethod
from typing import List, Callable, Any, Tuple, Dict, Type
from pathlib import Path
from datetime import datetime


class SortStrategy(ABC):
    """Base class for sorting strategies."""

    @abstractmethod
    def sort_key(self, item: Any) -> Any:
        """Get sort key for item.

        Args:
            item: File item to get key for

        Returns:
            Sort key value
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """Get strategy description.

        Returns:
            Human-readable description
        """
        pass


class NameSortStrategy(SortStrategy):
    """Sort by file name."""

    def sort_key(self, item: Any) -> Tuple[bool, bool, str]:
        """Sort by name (directories first, then alphabetically)."""
        return (not item.is_parent, not item.is_dir, item.name.lower())

    def description(self) -> str:
        """Get description."""
        return "Name"


class SizeSortStrategy(SortStrategy):
    """Sort by file size."""

    def sort_key(self, item: Any) -> Tuple[bool, bool, int]:
        """Sort by size (directories first, then by size)."""
        return (not item.is_parent, not item.is_dir, item.size)

    def description(self) -> str:
        """Get description."""
        return "Size"


class DateModifiedSortStrategy(SortStrategy):
    """Sort by modification date."""

    def sort_key(self, item: Any) -> Tuple[bool, bool, datetime]:
        """Sort by modification date (directories first, then by date)."""
        return (not item.is_parent, not item.is_dir, item.modified)

    def description(self) -> str:
        """Get description."""
        return "Date Modified"


class ExtensionSortStrategy(SortStrategy):
    """Sort by file extension."""

    def sort_key(self, item: Any) -> Tuple[bool, bool, str, str]:
        """Sort by extension (directories first, then by extension)."""
        ext = Path(item.name).suffix.lower() if not item.is_dir else ""
        return (not item.is_parent, not item.is_dir, ext, item.name.lower())

    def description(self) -> str:
        """Get description."""
        return "Extension"


class TypeSortStrategy(SortStrategy):
    """Sort by file type (directories, files, symlinks)."""

    def sort_key(self, item: Any) -> Tuple[int, str]:
        """Sort by type."""
        # Type priority: parent, dirs, files
        if item.is_parent:
            type_order = 0
        elif item.is_dir:
            type_order = 1
        else:
            type_order = 2

        return (type_order, item.name.lower())

    def description(self) -> str:
        """Get description."""
        return "Type"


class SortContext:
    """Context for applying sort strategies."""

    def __init__(self, strategy: SortStrategy, reverse: bool = False):
        """Initialize sort context.

        Args:
            strategy: Sort strategy to use
            reverse: Whether to reverse sort order
        """
        self.strategy = strategy
        self.reverse = reverse

    def sort(self, items: List[Any]) -> List[Any]:
        """Sort items using current strategy.

        Args:
            items: List of items to sort

        Returns:
            Sorted list
        """
        return sorted(items, key=self.strategy.sort_key, reverse=self.reverse)

    def set_strategy(self, strategy: SortStrategy) -> None:
        """Change sorting strategy.

        Args:
            strategy: New strategy
        """
        self.strategy = strategy

    def toggle_reverse(self) -> None:
        """Toggle reverse sort order."""
        self.reverse = not self.reverse

    def description(self) -> str:
        """Get current sort description."""
        order = "Descending" if self.reverse else "Ascending"
        return f"{self.strategy.description()} ({order})"


class SortStrategyFactory:
    """Factory for creating sort strategies."""

    _strategies: Dict[str, Type[SortStrategy]] = {
        "name": NameSortStrategy,
        "size": SizeSortStrategy,
        "modified": DateModifiedSortStrategy,
        "extension": ExtensionSortStrategy,
        "type": TypeSortStrategy,
    }

    @classmethod
    def create(cls, strategy_name: str) -> SortStrategy:
        """Create a sort strategy by name.

        Args:
            strategy_name: Name of strategy

        Returns:
            Sort strategy instance

        Raises:
            ValueError: If strategy name is invalid
        """
        strategy_class = cls._strategies.get(strategy_name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        return strategy_class()

    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy names."""
        return list(cls._strategies.keys())


# Pre-defined strategies for convenience
NAME_STRATEGY = NameSortStrategy()
SIZE_STRATEGY = SizeSortStrategy()
DATE_STRATEGY = DateModifiedSortStrategy()
EXTENSION_STRATEGY = ExtensionSortStrategy()
TYPE_STRATEGY = TypeSortStrategy()
