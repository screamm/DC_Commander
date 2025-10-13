"""Group selection feature for Modern Commander.

Provides wildcard-based group selection (Gray +/-/*) similar to Norton Commander.
"""

from pathlib import Path
from typing import List, Set, Any
import fnmatch
from components.file_panel import FileItem


class GroupSelector:
    """Handles group selection operations with wildcard patterns."""

    def __init__(self) -> None:
        """Initialize group selector."""
        pass

    def select_matching(self, items: List[FileItem], pattern: str, 
                       case_sensitive: bool = False) -> List[FileItem]:
        """Select files matching wildcard pattern.
        
        Args:
            items: List of file items to check
            pattern: Wildcard pattern (e.g., "*.py", "test_*")
            case_sensitive: Whether matching is case-sensitive
            
        Returns:
            List of items that match the pattern
        """
        matching = []
        
        for item in items:
            # Skip parent directory entry
            if item.is_parent:
                continue
            
            # Apply pattern matching
            name = item.name if case_sensitive else item.name.lower()
            check_pattern = pattern if case_sensitive else pattern.lower()
            
            if fnmatch.fnmatch(name, check_pattern):
                matching.append(item)
        
        return matching

    def deselect_matching(self, items: List[FileItem], pattern: str,
                         selected: Set[str], case_sensitive: bool = False) -> Set[str]:
        """Deselect files matching wildcard pattern.
        
        Args:
            items: List of file items
            pattern: Wildcard pattern
            selected: Set of currently selected file paths
            case_sensitive: Whether matching is case-sensitive
            
        Returns:
            Updated set of selected paths with matches removed
        """
        matching = self.select_matching(items, pattern, case_sensitive)
        
        # Remove matching items from selection
        for item in matching:
            selected.discard(str(item.path))
        
        return selected

    def invert_selection(self, items: List[FileItem], 
                        selected: Set[str]) -> Set[str]:
        """Invert current selection.
        
        Args:
            items: List of file items
            selected: Set of currently selected file paths
            
        Returns:
            New set with selection inverted
        """
        new_selection = set()
        
        for item in items:
            # Skip parent directory
            if item.is_parent:
                continue
            
            path_str = str(item.path)
            
            # If not selected, add to new selection
            # If selected, don't add (effectively deselecting)
            if path_str not in selected:
                new_selection.add(path_str)
        
        return new_selection

    def select_all(self, items: List[FileItem]) -> Set[str]:
        """Select all files (except parent directory).
        
        Args:
            items: List of file items
            
        Returns:
            Set of all file paths
        """
        selected = set()
        
        for item in items:
            if not item.is_parent:
                selected.add(str(item.path))
        
        return selected

    def clear_selection(self) -> Set[str]:
        """Clear all selections.
        
        Returns:
            Empty set
        """
        return set()
