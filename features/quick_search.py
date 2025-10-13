"""Quick search feature for Modern Commander.

Provides incremental search as you type, similar to Norton Commander.
"""

from pathlib import Path
from typing import List, Optional, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Represents a quick search match."""
    index: int
    name: str
    path: Path
    match_start: int
    match_end: int


class QuickSearch:
    """Handles quick search (type-to-filter) functionality."""

    def __init__(self) -> None:
        """Initialize quick search."""
        self.search_text: str = ""
        self.is_active: bool = False

    def activate(self) -> None:
        """Activate quick search mode."""
        self.is_active = True
        self.search_text = ""

    def deactivate(self) -> None:
        """Deactivate quick search mode."""
        self.is_active = False
        self.search_text = ""

    def add_char(self, char: str) -> None:
        """Add character to search text.

        Args:
            char: Character to add
        """
        if self.is_active:
            self.search_text += char

    def remove_char(self) -> None:
        """Remove last character from search text."""
        if self.is_active and self.search_text:
            self.search_text = self.search_text[:-1]

    def find_next_match(
        self, items: List[Any], current_index: int, case_sensitive: bool = False
    ) -> Optional[int]:
        """Find next item matching search text.

        Args:
            items: List of items to search (must have 'name' attribute)
            current_index: Current selection index
            case_sensitive: Whether search is case-sensitive

        Returns:
            Index of next matching item, or None if no match
        """
        if not self.search_text or not items:
            return None

        search_lower = self.search_text if case_sensitive else self.search_text.lower()

        # Search forward from current position
        for i in range(current_index + 1, len(items)):
            item_name = items[i].name if case_sensitive else items[i].name.lower()

            # Skip parent directory entry
            if hasattr(items[i], 'is_parent') and items[i].is_parent:
                continue

            if item_name.startswith(search_lower):
                return i

        # Wrap around to beginning
        for i in range(0, current_index + 1):
            item_name = items[i].name if case_sensitive else items[i].name.lower()

            # Skip parent directory entry
            if hasattr(items[i], 'is_parent') and items[i].is_parent:
                continue

            if item_name.startswith(search_lower):
                return i

        return None

    def find_all_matches(
        self, items: List[Any], case_sensitive: bool = False
    ) -> List[SearchResult]:
        """Find all items matching search text.

        Args:
            items: List of items to search
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of search results
        """
        if not self.search_text or not items:
            return []

        results = []
        search_lower = self.search_text if case_sensitive else self.search_text.lower()
        match_len = len(search_lower)

        for i, item in enumerate(items):
            # Skip parent directory entry
            if hasattr(item, 'is_parent') and item.is_parent:
                continue

            item_name = item.name if case_sensitive else item.name.lower()

            if item_name.startswith(search_lower):
                results.append(SearchResult(
                    index=i,
                    name=item.name,
                    path=item.path,
                    match_start=0,
                    match_end=match_len
                ))

        return results

    def clear(self) -> None:
        """Clear search text."""
        self.search_text = ""
