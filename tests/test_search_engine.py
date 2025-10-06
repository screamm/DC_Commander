"""
Unit tests for search engine functionality

Tests cover:
- File search with wildcards and regex
- Content search with context
- Filter operations and criteria
- Performance with large file sets
- Edge cases and error handling
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from features.search_engine import (
    FileSearch, SearchOptions, FilterCriteria, FileFilter,
    FilterOperator, LogicalOperator, SearchResult,
    filter_files, search_files, search_content, get_matching_files
)


class TestSearchOptions(unittest.TestCase):
    """Test SearchOptions configuration"""

    def test_default_options(self):
        """Test default search options"""
        options = SearchOptions()
        self.assertFalse(options.case_sensitive)
        self.assertFalse(options.use_regex)
        self.assertTrue(options.search_subdirectories)
        self.assertFalse(options.follow_symlinks)

    def test_exclude_directory(self):
        """Test directory exclusion"""
        options = SearchOptions()
        self.assertTrue(options.should_exclude_directory('.git'))
        self.assertTrue(options.should_exclude_directory('__pycache__'))
        self.assertFalse(options.should_exclude_directory('src'))

    def test_exclude_file_pattern(self):
        """Test file exclusion patterns"""
        options = SearchOptions(exclude_patterns=['*.tmp', '*.log'])

        self.assertTrue(options.should_exclude_file(Path('test.tmp')))
        self.assertTrue(options.should_exclude_file(Path('debug.log')))
        self.assertFalse(options.should_exclude_file(Path('test.py')))

    def test_extension_filter(self):
        """Test extension filtering"""
        options = SearchOptions(file_extensions=['.py', '.txt'])

        self.assertTrue(options.matches_extension_filter(Path('test.py')))
        self.assertTrue(options.matches_extension_filter(Path('readme.txt')))
        self.assertFalse(options.matches_extension_filter(Path('image.jpg')))


class TestFileFilter(unittest.TestCase):
    """Test FileFilter operations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / 'test.txt'
        self.test_file.write_text('test content')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_name_filter_equals(self):
        """Test name filter with equals operator"""
        filter = FileFilter('name', FilterOperator.EQUALS, 'test.txt')
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('name', FilterOperator.EQUALS, 'other.txt')
        self.assertFalse(filter.matches(self.test_file))

    def test_name_filter_contains(self):
        """Test name filter with contains operator"""
        filter = FileFilter('name', FilterOperator.CONTAINS, 'test')
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('name', FilterOperator.CONTAINS, 'other')
        self.assertFalse(filter.matches(self.test_file))

    def test_name_filter_regex(self):
        """Test name filter with regex"""
        filter = FileFilter('name', FilterOperator.REGEX, r'test\.\w+')
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('name', FilterOperator.REGEX, r'\d+\.txt')
        self.assertFalse(filter.matches(self.test_file))

    def test_size_filter(self):
        """Test size filter operations"""
        file_size = self.test_file.stat().st_size

        filter = FileFilter('size', FilterOperator.GREATER, file_size - 1)
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('size', FilterOperator.LESS, file_size + 1)
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('size', FilterOperator.EQUALS, file_size)
        self.assertTrue(filter.matches(self.test_file))

    def test_extension_filter(self):
        """Test extension filter"""
        filter = FileFilter('extension', FilterOperator.EQUALS, '.txt')
        self.assertTrue(filter.matches(self.test_file))

        filter = FileFilter('extension', FilterOperator.EQUALS, '.py')
        self.assertFalse(filter.matches(self.test_file))


class TestFilterCriteria(unittest.TestCase):
    """Test FilterCriteria combinations"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / 'test.txt'
        self.test_file.write_text('test content')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_and_operator(self):
        """Test AND operator"""
        criteria = FilterCriteria(
            filters=[
                FileFilter('name', FilterOperator.CONTAINS, 'test'),
                FileFilter('extension', FilterOperator.EQUALS, '.txt')
            ],
            operator=LogicalOperator.AND
        )
        self.assertTrue(criteria.matches(self.test_file))

        criteria = FilterCriteria(
            filters=[
                FileFilter('name', FilterOperator.CONTAINS, 'test'),
                FileFilter('extension', FilterOperator.EQUALS, '.py')
            ],
            operator=LogicalOperator.AND
        )
        self.assertFalse(criteria.matches(self.test_file))

    def test_or_operator(self):
        """Test OR operator"""
        criteria = FilterCriteria(
            filters=[
                FileFilter('name', FilterOperator.CONTAINS, 'other'),
                FileFilter('extension', FilterOperator.EQUALS, '.txt')
            ],
            operator=LogicalOperator.OR
        )
        self.assertTrue(criteria.matches(self.test_file))

    def test_not_operator(self):
        """Test NOT operator"""
        criteria = FilterCriteria(
            filters=[
                FileFilter('extension', FilterOperator.EQUALS, '.py')
            ],
            operator=LogicalOperator.NOT
        )
        self.assertTrue(criteria.matches(self.test_file))


class TestFileSearch(unittest.TestCase):
    """Test FileSearch functionality"""

    def setUp(self):
        """Set up test environment with sample file structure"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create test file structure
        (self.root / 'test1.txt').write_text('hello world')
        (self.root / 'test2.py').write_text('print("hello")')
        (self.root / 'README.md').write_text('# Test Project')

        # Subdirectory
        sub_dir = self.root / 'subdir'
        sub_dir.mkdir()
        (sub_dir / 'test3.txt').write_text('nested file')
        (sub_dir / 'data.json').write_text('{"key": "value"}')

        # Excluded directory
        excluded = self.root / '__pycache__'
        excluded.mkdir()
        (excluded / 'cache.pyc').write_text('bytecode')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_search_wildcard_pattern(self):
        """Test search with wildcard pattern"""
        searcher = FileSearch()
        results = list(searcher.search_files(self.root, '*.txt'))

        self.assertEqual(len(results), 2)  # test1.txt and test3.txt
        result_names = {r.path.name for r in results}
        self.assertIn('test1.txt', result_names)
        self.assertIn('test3.txt', result_names)

    def test_search_exact_match(self):
        """Test search with exact filename"""
        searcher = FileSearch()
        results = list(searcher.search_files(self.root, 'README.md'))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'README.md')

    def test_search_regex_pattern(self):
        """Test search with regex pattern"""
        searcher = FileSearch()
        options = SearchOptions(use_regex=True)
        results = list(searcher.search_files(self.root, r'test\d+\.txt', options))

        self.assertEqual(len(results), 2)  # test1.txt and test3.txt

    def test_search_case_sensitive(self):
        """Test case-sensitive search"""
        # Create files with different cases
        (self.root / 'Test.txt').write_text('mixed case')

        searcher = FileSearch()

        # Case insensitive (default)
        results = list(searcher.search_files(self.root, 'test*'))
        self.assertGreaterEqual(len(results), 3)

        # Case sensitive
        options = SearchOptions(case_sensitive=True)
        results = list(searcher.search_files(self.root, 'test*', options))
        result_names = {r.path.name for r in results}
        self.assertNotIn('Test.txt', result_names)

    def test_search_no_subdirectories(self):
        """Test search without subdirectories"""
        searcher = FileSearch()
        options = SearchOptions(search_subdirectories=False)
        results = list(searcher.search_files(self.root, '*.txt', options))

        # Should only find test1.txt, not test3.txt in subdir
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'test1.txt')

    def test_search_excluded_directories(self):
        """Test that excluded directories are skipped"""
        searcher = FileSearch()
        results = list(searcher.search_files(self.root, '*.pyc'))

        # Should not find cache.pyc in __pycache__
        self.assertEqual(len(results), 0)

    def test_search_max_depth(self):
        """Test max depth limitation"""
        # Create deeper structure
        deep_dir = self.root / 'level1' / 'level2' / 'level3'
        deep_dir.mkdir(parents=True)
        (deep_dir / 'deep.txt').write_text('deep file')

        searcher = FileSearch()
        options = SearchOptions(max_depth=2)
        results = list(searcher.search_files(self.root, '*.txt', options))

        result_paths = [r.path for r in results]
        # Should not find deep.txt
        self.assertNotIn(deep_dir / 'deep.txt', result_paths)

    def test_search_max_results(self):
        """Test max results limitation"""
        searcher = FileSearch()
        options = SearchOptions(max_results=2)
        results = list(searcher.search_files(self.root, '*', options))

        self.assertLessEqual(len(results), 2)

    def test_search_extension_filter(self):
        """Test file extension filtering"""
        searcher = FileSearch()
        options = SearchOptions(file_extensions=['.txt', '.md'])
        results = list(searcher.search_files(self.root, '*', options))

        for result in results:
            self.assertIn(result.path.suffix, ['.txt', '.md'])

    def test_content_search(self):
        """Test content search"""
        searcher = FileSearch()
        results = list(searcher.search_content(self.root, 'hello'))

        self.assertGreaterEqual(len(results), 2)  # test1.txt and test2.py

        # Check that matched line is captured
        for result in results:
            self.assertIsNotNone(result.matched_line)
            self.assertIn('hello', result.matched_line.lower())

    def test_content_search_regex(self):
        """Test content search with regex"""
        searcher = FileSearch()
        options = SearchOptions(use_regex=True)
        results = list(searcher.search_content(self.root, r'print\(.*\)', options))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'test2.py')

    def test_content_search_with_context(self):
        """Test content search with context lines"""
        # Create file with multiple lines
        multi_line = self.root / 'multi.txt'
        multi_line.write_text('line1\nline2\nmatch here\nline4\nline5')

        searcher = FileSearch()
        results = list(searcher.search_content(self.root, 'match', context_lines=1))

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIsNotNone(result.match_context)
        self.assertIn('line2', result.match_context)
        self.assertIn('line4', result.match_context)

    def test_stop_search(self):
        """Test stopping search operation"""
        # Create many files
        for i in range(100):
            (self.root / f'file{i}.txt').write_text(f'content {i}')

        searcher = FileSearch()

        # Start search and stop immediately
        searcher.stop()
        results = list(searcher.search_files(self.root, '*'))

        # Should stop early
        self.assertLess(len(results), 100)


class TestFilterFiles(unittest.TestCase):
    """Test filter_files convenience function"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create test files
        self.files = [
            self.root / 'small.txt',
            self.root / 'large.txt',
            self.root / 'test.py'
        ]

        self.files[0].write_text('small')
        self.files[1].write_text('x' * 10000)
        self.files[2].write_text('python')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_filter_by_size(self):
        """Test filtering by file size"""
        criteria = FilterCriteria(
            filters=[FileFilter('size', FilterOperator.GREATER, 100)]
        )

        filtered = filter_files(self.files, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, 'large.txt')

    def test_filter_by_extension(self):
        """Test filtering by extension"""
        criteria = FilterCriteria(
            filters=[FileFilter('extension', FilterOperator.EQUALS, '.txt')]
        )

        filtered = filter_files(self.files, criteria)
        self.assertEqual(len(filtered), 2)

    def test_combined_filters(self):
        """Test combined filter criteria"""
        criteria = FilterCriteria(
            filters=[
                FileFilter('extension', FilterOperator.EQUALS, '.txt'),
                FileFilter('size', FilterOperator.GREATER, 100)
            ],
            operator=LogicalOperator.AND
        )

        filtered = filter_files(self.files, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].name, 'large.txt')


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        (self.root / 'test.txt').write_text('test content')
        (self.root / 'data.json').write_text('{"key": "value"}')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_search_files_function(self):
        """Test search_files convenience function"""
        results = search_files(self.root, '*.txt')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path.name, 'test.txt')

    def test_search_content_function(self):
        """Test search_content convenience function"""
        results = search_content(self.root, 'test')

        self.assertGreaterEqual(len(results), 1)
        self.assertIsNotNone(results[0].matched_line)

    def test_get_matching_files_function(self):
        """Test get_matching_files convenience function"""
        criteria = FilterCriteria(
            filters=[FileFilter('extension', FilterOperator.EQUALS, '.txt')]
        )

        results = get_matching_files(self.root, criteria)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'test.txt')


class TestSearchResult(unittest.TestCase):
    """Test SearchResult dataclass"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / 'test.txt'
        self.test_file.write_text('content')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_result_auto_populate(self):
        """Test automatic metadata population"""
        result = SearchResult(path=self.test_file)

        self.assertIsNotNone(result.file_size)
        self.assertIsNotNone(result.modified_time)
        self.assertGreater(result.file_size, 0)

    def test_result_with_match_info(self):
        """Test result with match information"""
        result = SearchResult(
            path=self.test_file,
            matched_line='test line',
            line_number=42
        )

        self.assertEqual(result.matched_line, 'test line')
        self.assertEqual(result.line_number, 42)


class TestPerformance(unittest.TestCase):
    """Performance tests for search operations"""

    def setUp(self):
        """Set up large test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # Create many files for performance testing
        for i in range(100):
            (self.root / f'file{i}.txt').write_text(f'content {i}')

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)

    def test_large_search_performance(self):
        """Test search performance with many files"""
        import time

        searcher = FileSearch()
        start = time.time()
        results = list(searcher.search_files(self.root, '*.txt'))
        elapsed = time.time() - start

        self.assertEqual(len(results), 100)
        # Should complete in reasonable time
        self.assertLess(elapsed, 5.0)

    def test_generator_efficiency(self):
        """Test that search uses generators efficiently"""
        searcher = FileSearch()
        options = SearchOptions(max_results=10)

        # Generator should stop early
        results = list(searcher.search_files(self.root, '*.txt', options))
        self.assertEqual(len(results), 10)


if __name__ == '__main__':
    unittest.main()
