"""Regression tests for Bug 1: FileViewer scroll_offset AttributeError.

FileViewer.__init__ previously assigned ``self.scroll_offset = 0``, which
raised ``AttributeError: can't set attribute`` because ``Screen`` (the base
class) exposes ``scroll_offset`` as a read-only property (returning a 2-D
``Offset`` object, not an int).

Fix: renamed the internal attribute to ``_content_scroll_y`` and updated all
internal usages within ``FileViewer`` to use that name, avoiding any
shadow of ``Screen.scroll_offset`` entirely.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from features.file_viewer import FileViewer


# ---------------------------------------------------------------------------
# Unit tests (no Textual harness needed)
# ---------------------------------------------------------------------------


def test_file_viewer_init_does_not_raise(tmp_path: Path) -> None:
    """Constructing FileViewer must not raise AttributeError on scroll_offset."""
    sample = tmp_path / "sample.txt"
    sample.write_text("hello\nworld\n", encoding="utf-8")

    # This used to raise AttributeError: can't set attribute
    viewer = FileViewer(file_path=sample)
    # Construction succeeded — verify initial state
    assert viewer._content_scroll_y == 0


def test_internal_scroll_attribute_starts_at_zero(tmp_path: Path) -> None:
    """The private _content_scroll_y attribute is initialised to 0."""
    sample = tmp_path / "sample.txt"
    sample.write_text("x\n", encoding="utf-8")

    viewer = FileViewer(file_path=sample)
    assert hasattr(viewer, "_content_scroll_y")
    assert viewer._content_scroll_y == 0


def test_internal_scroll_attribute_is_writable(tmp_path: Path) -> None:
    """_content_scroll_y must be assignable without raising."""
    sample = tmp_path / "sample.txt"
    sample.write_text("line1\n", encoding="utf-8")

    viewer = FileViewer(file_path=sample)
    viewer._content_scroll_y = 5
    assert viewer._content_scroll_y == 5


def test_screen_scroll_offset_not_shadowed(tmp_path: Path) -> None:
    """FileViewer must not shadow Screen.scroll_offset.

    Screen.scroll_offset is a property returning Offset (2-D).  FileViewer
    must not override it with an int attribute or property, otherwise Textual
    internals that call scroll_offset.x / scroll_offset.y will break.
    """
    from textual.geometry import Offset

    sample = tmp_path / "sample.txt"
    sample.write_text("x\n", encoding="utf-8")

    viewer = FileViewer(file_path=sample)
    # Before mount, Screen.scroll_offset should still be accessible and
    # return an Offset (or at minimum not an int).  In an unmounted state
    # scroll_x and scroll_y default to 0.
    result = type(viewer).scroll_offset.fget(viewer)  # type: ignore[attr-defined]
    assert isinstance(result, Offset), (
        f"Screen.scroll_offset must return Offset, got {type(result)}"
    )


pytestmark = pytest.mark.asyncio


async def test_file_viewer_scroll_offset_consistent_after_assignment(tmp_path: Path) -> None:
    """After assigning _content_scroll_y, reading it back returns the same value."""
    sample = tmp_path / "sample.txt"
    sample.write_text("line1\nline2\nline3\n", encoding="utf-8")

    viewer = FileViewer(file_path=sample)
    for value in (0, 1, 2, 10):
        viewer._content_scroll_y = value
        assert viewer._content_scroll_y == value, (
            f"_content_scroll_y round-trip failed for value {value}"
        )
