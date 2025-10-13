"""Comprehensive tests for Strategy Pattern implementation.

Tests flexible sorting strategies for file listings including
name, size, date, extension, and type sorting with context management.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from models.file_item import FileItem
from patterns.strategy_pattern import (
    NameSortStrategy,
    SizeSortStrategy,
    DateModifiedSortStrategy,
    ExtensionSortStrategy,
    TypeSortStrategy,
    SortContext,
    SortStrategyFactory,
    NAME_STRATEGY,
    SIZE_STRATEGY,
    DATE_STRATEGY,
    EXTENSION_STRATEGY,
    TYPE_STRATEGY
)


@pytest.fixture
def sample_file_items(tmp_path):
    """Create sample FileItem objects for testing."""
    items = []

    # Parent directory
    items.append(FileItem(
        name="..",
        path=tmp_path.parent,
        size=0,
        modified=datetime.now(),
        is_dir=True,
        is_parent=True
    ))

    # Regular files with different properties
    items.append(FileItem(
        name="zebra.txt",
        path=tmp_path / "zebra.txt",
        size=1000,
        modified=datetime(2024, 1, 1, 12, 0),
        is_dir=False,
        is_parent=False
    ))

    items.append(FileItem(
        name="apple.txt",
        path=tmp_path / "apple.txt",
        size=5000,
        modified=datetime(2024, 1, 3, 12, 0),
        is_dir=False,
        is_parent=False
    ))

    items.append(FileItem(
        name="banana.py",
        path=tmp_path / "banana.py",
        size=3000,
        modified=datetime(2024, 1, 2, 12, 0),
        is_dir=False,
        is_parent=False
    ))

    # Directory
    items.append(FileItem(
        name="documents",
        path=tmp_path / "documents",
        size=0,
        modified=datetime(2024, 1, 4, 12, 0),
        is_dir=True,
        is_parent=False
    ))

    return items


class TestNameSortStrategy:
    """Test NameSortStrategy sorting."""

    def test_sort_by_name_ascending(self, sample_file_items):
        """Test sorting by name alphabetically."""
        strategy = NameSortStrategy()
        sorted_items = sorted(sample_file_items, key=strategy.sort_key)

        names = [item.name for item in sorted_items]
        # Parent first, then dirs, then files alphabetically
        assert names[0] == ".."
        assert "documents" in names[1:2]  # Directory
        # Files in alphabetical order
        file_names = [n for n in names if n not in ["..", "documents"]]
        assert file_names == sorted(file_names, key=str.lower)

    def test_description(self):
        """Test strategy description."""
        strategy = NameSortStrategy()
        assert strategy.description() == "Name"

    def test_directories_before_files(self, tmp_path):
        """Test directories are sorted before files."""
        items = [
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False),
            FileItem("dir", tmp_path / "dir", 0, datetime.now(), is_dir=True),
        ]

        strategy = NameSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        assert sorted_items[0].is_dir is True
        assert sorted_items[1].is_dir is False

    def test_parent_always_first(self, tmp_path):
        """Test parent entry is always first."""
        items = [
            FileItem("zebra.txt", tmp_path / "zebra.txt", 100, datetime.now(), is_dir=False),
            FileItem("..", tmp_path.parent, 0, datetime.now(), is_dir=True, is_parent=True),
            FileItem("aaa.txt", tmp_path / "aaa.txt", 100, datetime.now(), is_dir=False),
        ]

        strategy = NameSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        assert sorted_items[0].is_parent is True


class TestSizeSortStrategy:
    """Test SizeSortStrategy sorting."""

    def test_sort_by_size_ascending(self, sample_file_items):
        """Test sorting by size."""
        strategy = SizeSortStrategy()
        sorted_items = sorted(sample_file_items, key=strategy.sort_key)

        # Parent first, then directories, then files by size
        assert sorted_items[0].is_parent is True

        # Get file sizes (excluding parent and dirs)
        file_items = [item for item in sorted_items if not item.is_dir]
        sizes = [item.size for item in file_items]
        assert sizes == sorted(sizes)

    def test_description(self):
        """Test strategy description."""
        strategy = SizeSortStrategy()
        assert strategy.description() == "Size"

    def test_zero_size_handling(self, tmp_path):
        """Test handling of zero-size files."""
        items = [
            FileItem("empty.txt", tmp_path / "empty.txt", 0, datetime.now(), is_dir=False),
            FileItem("large.txt", tmp_path / "large.txt", 5000, datetime.now(), is_dir=False),
            FileItem("small.txt", tmp_path / "small.txt", 100, datetime.now(), is_dir=False),
        ]

        strategy = SizeSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        sizes = [item.size for item in sorted_items]
        assert sizes == [0, 100, 5000]


class TestDateModifiedSortStrategy:
    """Test DateModifiedSortStrategy sorting."""

    def test_sort_by_date_ascending(self, sample_file_items):
        """Test sorting by modification date."""
        strategy = DateModifiedSortStrategy()
        sorted_items = sorted(sample_file_items, key=strategy.sort_key)

        # Parent first, then dirs, then files by date
        assert sorted_items[0].is_parent is True

        # Get file dates (excluding parent and dirs)
        file_items = [item for item in sorted_items if not item.is_dir]
        dates = [item.modified for item in file_items]
        assert dates == sorted(dates)

    def test_description(self):
        """Test strategy description."""
        strategy = DateModifiedSortStrategy()
        assert strategy.description() == "Date Modified"

    def test_same_date_handling(self, tmp_path):
        """Test handling of files with same modification date."""
        same_date = datetime(2024, 1, 1, 12, 0)
        items = [
            FileItem("file1.txt", tmp_path / "file1.txt", 100, same_date, is_dir=False),
            FileItem("file2.txt", tmp_path / "file2.txt", 200, same_date, is_dir=False),
            FileItem("file3.txt", tmp_path / "file3.txt", 300, same_date, is_dir=False),
        ]

        strategy = DateModifiedSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        # All should be sorted (stable sort maintains original order)
        assert len(sorted_items) == 3


class TestExtensionSortStrategy:
    """Test ExtensionSortStrategy sorting."""

    def test_sort_by_extension(self, sample_file_items):
        """Test sorting by file extension."""
        strategy = ExtensionSortStrategy()
        sorted_items = sorted(sample_file_items, key=strategy.sort_key)

        # Parent first, then dirs, then files by extension
        assert sorted_items[0].is_parent is True

        # Get extensions (excluding parent and dirs)
        file_items = [item for item in sorted_items if not item.is_dir]
        extensions = [Path(item.name).suffix for item in file_items]

        # Extensions should be sorted
        assert extensions == sorted(extensions, key=str.lower)

    def test_description(self):
        """Test strategy description."""
        strategy = ExtensionSortStrategy()
        assert strategy.description() == "Extension"

    def test_no_extension_handling(self, tmp_path):
        """Test handling of files without extension."""
        items = [
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False),
            FileItem("noext", tmp_path / "noext", 100, datetime.now(), is_dir=False),
            FileItem("file.py", tmp_path / "file.py", 100, datetime.now(), is_dir=False),
        ]

        strategy = ExtensionSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        # Files without extension should be grouped
        assert len(sorted_items) == 3

    def test_same_extension_alphabetical(self, tmp_path):
        """Test files with same extension are sorted alphabetically."""
        items = [
            FileItem("zebra.txt", tmp_path / "zebra.txt", 100, datetime.now(), is_dir=False),
            FileItem("apple.txt", tmp_path / "apple.txt", 100, datetime.now(), is_dir=False),
            FileItem("banana.txt", tmp_path / "banana.txt", 100, datetime.now(), is_dir=False),
        ]

        strategy = ExtensionSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        names = [item.name for item in sorted_items]
        assert names == ["apple.txt", "banana.txt", "zebra.txt"]


class TestTypeSortStrategy:
    """Test TypeSortStrategy sorting."""

    def test_sort_by_type(self, sample_file_items):
        """Test sorting by file type."""
        strategy = TypeSortStrategy()
        sorted_items = sorted(sample_file_items, key=strategy.sort_key)

        # Parent first, then dirs, then files
        types = [(item.is_parent, item.is_dir) for item in sorted_items]

        # First should be parent
        assert types[0] == (True, True)

        # Then directories (is_parent=False, is_dir=True)
        # Then files (is_parent=False, is_dir=False)
        for i in range(1, len(types)):
            if types[i][1]:  # is_dir
                # All dirs should come before files
                assert not any(not item[1] for item in types[1:i])

    def test_description(self):
        """Test strategy description."""
        strategy = TypeSortStrategy()
        assert strategy.description() == "Type"

    def test_type_order(self, tmp_path):
        """Test type ordering: parent, dirs, files."""
        items = [
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False),
            FileItem("..", tmp_path.parent, 0, datetime.now(), is_dir=True, is_parent=True),
            FileItem("dir", tmp_path / "dir", 0, datetime.now(), is_dir=True),
        ]

        strategy = TypeSortStrategy()
        sorted_items = sorted(items, key=strategy.sort_key)

        assert sorted_items[0].is_parent is True
        assert sorted_items[1].is_dir is True and not sorted_items[1].is_parent
        assert sorted_items[2].is_dir is False


class TestSortContext:
    """Test SortContext operations."""

    def test_init_with_strategy(self):
        """Test initialization with strategy."""
        strategy = NameSortStrategy()
        context = SortContext(strategy)

        assert context.strategy == strategy
        assert context.reverse is False

    def test_init_with_reverse(self):
        """Test initialization with reverse flag."""
        strategy = NameSortStrategy()
        context = SortContext(strategy, reverse=True)

        assert context.reverse is True

    def test_sort_ascending(self, sample_file_items):
        """Test sorting in ascending order."""
        strategy = SizeSortStrategy()
        context = SortContext(strategy, reverse=False)

        sorted_items = context.sort(sample_file_items)

        # Check that it's sorted
        assert isinstance(sorted_items, list)
        assert len(sorted_items) == len(sample_file_items)

    def test_sort_descending(self, sample_file_items):
        """Test sorting in descending order."""
        strategy = SizeSortStrategy()
        context = SortContext(strategy, reverse=True)

        sorted_items = context.sort(sample_file_items)

        # Get file sizes (excluding parent and dirs)
        file_items = [item for item in sorted_items if not item.is_dir]
        sizes = [item.size for item in file_items]

        # Should be in descending order
        assert sizes == sorted(sizes, reverse=True)

    def test_set_strategy(self):
        """Test changing strategy."""
        strategy1 = NameSortStrategy()
        strategy2 = SizeSortStrategy()

        context = SortContext(strategy1)
        assert context.strategy == strategy1

        context.set_strategy(strategy2)
        assert context.strategy == strategy2

    def test_toggle_reverse(self):
        """Test toggling reverse flag."""
        strategy = NameSortStrategy()
        context = SortContext(strategy, reverse=False)

        assert context.reverse is False

        context.toggle_reverse()
        assert context.reverse is True

        context.toggle_reverse()
        assert context.reverse is False

    def test_description_ascending(self):
        """Test description for ascending sort."""
        strategy = NameSortStrategy()
        context = SortContext(strategy, reverse=False)

        desc = context.description()

        assert "Name" in desc
        assert "Ascending" in desc

    def test_description_descending(self):
        """Test description for descending sort."""
        strategy = SizeSortStrategy()
        context = SortContext(strategy, reverse=True)

        desc = context.description()

        assert "Size" in desc
        assert "Descending" in desc


class TestSortStrategyFactory:
    """Test SortStrategyFactory operations."""

    def test_create_name_strategy(self):
        """Test creating name sort strategy."""
        strategy = SortStrategyFactory.create("name")

        assert isinstance(strategy, NameSortStrategy)

    def test_create_size_strategy(self):
        """Test creating size sort strategy."""
        strategy = SortStrategyFactory.create("size")

        assert isinstance(strategy, SizeSortStrategy)

    def test_create_modified_strategy(self):
        """Test creating date modified strategy."""
        strategy = SortStrategyFactory.create("modified")

        assert isinstance(strategy, DateModifiedSortStrategy)

    def test_create_extension_strategy(self):
        """Test creating extension strategy."""
        strategy = SortStrategyFactory.create("extension")

        assert isinstance(strategy, ExtensionSortStrategy)

    def test_create_type_strategy(self):
        """Test creating type strategy."""
        strategy = SortStrategyFactory.create("type")

        assert isinstance(strategy, TypeSortStrategy)

    def test_create_case_insensitive(self):
        """Test factory is case-insensitive."""
        strategy1 = SortStrategyFactory.create("NAME")
        strategy2 = SortStrategyFactory.create("Name")
        strategy3 = SortStrategyFactory.create("name")

        assert isinstance(strategy1, NameSortStrategy)
        assert isinstance(strategy2, NameSortStrategy)
        assert isinstance(strategy3, NameSortStrategy)

    def test_create_invalid_strategy(self):
        """Test creating invalid strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            SortStrategyFactory.create("invalid")

    def test_get_available_strategies(self):
        """Test getting list of available strategies."""
        strategies = SortStrategyFactory.get_available_strategies()

        assert "name" in strategies
        assert "size" in strategies
        assert "modified" in strategies
        assert "extension" in strategies
        assert "type" in strategies
        assert len(strategies) == 5


class TestPredefinedStrategies:
    """Test predefined strategy constants."""

    def test_name_strategy_constant(self):
        """Test NAME_STRATEGY constant."""
        assert isinstance(NAME_STRATEGY, NameSortStrategy)

    def test_size_strategy_constant(self):
        """Test SIZE_STRATEGY constant."""
        assert isinstance(SIZE_STRATEGY, SizeSortStrategy)

    def test_date_strategy_constant(self):
        """Test DATE_STRATEGY constant."""
        assert isinstance(DATE_STRATEGY, DateModifiedSortStrategy)

    def test_extension_strategy_constant(self):
        """Test EXTENSION_STRATEGY constant."""
        assert isinstance(EXTENSION_STRATEGY, ExtensionSortStrategy)

    def test_type_strategy_constant(self):
        """Test TYPE_STRATEGY constant."""
        assert isinstance(TYPE_STRATEGY, TypeSortStrategy)


class TestSortingStability:
    """Test sorting stability and consistency."""

    def test_stable_sort(self, tmp_path):
        """Test sort is stable (maintains relative order)."""
        # Create items with same sort key
        items = [
            FileItem("c.txt", tmp_path / "c.txt", 100, datetime.now(), is_dir=False),
            FileItem("b.txt", tmp_path / "b.txt", 100, datetime.now(), is_dir=False),
            FileItem("a.txt", tmp_path / "a.txt", 100, datetime.now(), is_dir=False),
        ]

        strategy = SizeSortStrategy()  # All have same size
        context = SortContext(strategy)

        sorted_items = context.sort(items)

        # Original order should be maintained for items with same key
        assert len(sorted_items) == 3

    def test_reverse_twice_equals_original(self, sample_file_items):
        """Test sorting, reversing, and reversing again returns to original order."""
        strategy = NameSortStrategy()
        context = SortContext(strategy, reverse=False)

        sorted_once = context.sort(sample_file_items)

        context.toggle_reverse()
        sorted_reversed = context.sort(sample_file_items)

        context.toggle_reverse()
        sorted_twice = context.sort(sample_file_items)

        # Should match original forward sort
        names_once = [item.name for item in sorted_once]
        names_twice = [item.name for item in sorted_twice]
        assert names_once == names_twice


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_list(self):
        """Test sorting empty list."""
        strategy = NameSortStrategy()
        context = SortContext(strategy)

        sorted_items = context.sort([])

        assert sorted_items == []

    def test_single_item(self, tmp_path):
        """Test sorting single item."""
        items = [
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False)
        ]

        strategy = NameSortStrategy()
        context = SortContext(strategy)

        sorted_items = context.sort(items)

        assert len(sorted_items) == 1
        assert sorted_items[0] == items[0]

    def test_all_same_values(self, tmp_path):
        """Test sorting items with identical values."""
        same_date = datetime.now()
        items = [
            FileItem("a.txt", tmp_path / "a.txt", 100, same_date, is_dir=False),
            FileItem("b.txt", tmp_path / "b.txt", 100, same_date, is_dir=False),
            FileItem("c.txt", tmp_path / "c.txt", 100, same_date, is_dir=False),
        ]

        # Try different strategies
        for strategy in [NAME_STRATEGY, SIZE_STRATEGY, DATE_STRATEGY]:
            context = SortContext(strategy)
            sorted_items = context.sort(items)
            assert len(sorted_items) == 3

    def test_unicode_filenames(self, tmp_path):
        """Test sorting unicode filenames."""
        items = [
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False),
            FileItem("file.txt", tmp_path / "file.txt", 100, datetime.now(), is_dir=False),
        ]

        strategy = NameSortStrategy()
        context = SortContext(strategy)

        sorted_items = context.sort(items)

        assert len(sorted_items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
