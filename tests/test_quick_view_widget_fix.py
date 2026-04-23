"""Regression tests for Bug 3: QuickViewWidget missing preview_file / clear_preview.

``modern_commander.py``'s ``_update_quick_view`` called
``QuickViewWidget.preview_file(path)`` and ``QuickViewWidget.clear_preview()``
but neither method existed. Any invocation raised ``AttributeError``.

Fix: added ``preview_file(path)`` and ``clear_preview()`` as thin wrappers
over the existing ``set_file()`` method.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from components.quick_view_widget import QuickViewWidget


# ---------------------------------------------------------------------------
# Unit tests — API existence and delegation
# ---------------------------------------------------------------------------


def test_preview_file_method_exists() -> None:
    """QuickViewWidget must expose a preview_file method."""
    assert callable(getattr(QuickViewWidget, "preview_file", None)), (
        "QuickViewWidget.preview_file does not exist"
    )


def test_clear_preview_method_exists() -> None:
    """QuickViewWidget must expose a clear_preview method."""
    assert callable(getattr(QuickViewWidget, "clear_preview", None)), (
        "QuickViewWidget.clear_preview does not exist"
    )


def test_preview_file_sets_current_file(tmp_path: Path) -> None:
    """preview_file(path) must set current_file to the given path."""
    sample = tmp_path / "hello.txt"
    sample.write_text("hi", encoding="utf-8")

    widget = QuickViewWidget()
    widget.preview_file(sample)
    assert widget.current_file == sample


def test_clear_preview_clears_current_file(tmp_path: Path) -> None:
    """clear_preview() must set current_file to None."""
    sample = tmp_path / "hello.txt"
    sample.write_text("hi", encoding="utf-8")

    widget = QuickViewWidget()
    widget.preview_file(sample)
    widget.clear_preview()
    assert widget.current_file is None


def test_preview_file_delegates_to_set_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """preview_file must delegate to set_file."""
    sample = tmp_path / "hello.txt"
    sample.write_text("hi", encoding="utf-8")

    widget = QuickViewWidget()
    calls: list[object] = []
    monkeypatch.setattr(widget, "set_file", lambda p: calls.append(p))

    widget.preview_file(sample)
    assert calls == [sample]


def test_clear_preview_delegates_to_set_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """clear_preview must delegate to set_file(None)."""
    widget = QuickViewWidget()
    calls: list[object] = []
    monkeypatch.setattr(widget, "set_file", lambda p: calls.append(p))

    widget.clear_preview()
    assert calls == [None]


# ---------------------------------------------------------------------------
# Integration smoke-test with Textual pilot
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


async def test_quick_view_toggle_does_not_raise(tmp_path: Path) -> None:
    """Calling preview_file then clear_preview on a mounted widget must not raise."""
    from textual.app import App, ComposeResult

    sample = tmp_path / "sample.txt"
    sample.write_text("hello world\n", encoding="utf-8")

    class _Host(App):
        def compose(self) -> ComposeResult:
            yield QuickViewWidget(id="qv")

        def on_mount(self) -> None:
            self.get_widget_by_id("qv").preview_file(sample)  # type: ignore[attr-defined]

    app = _Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        qv: QuickViewWidget = app.get_widget_by_id("qv")  # type: ignore[assignment]
        # clear_preview must not raise
        qv.clear_preview()
        await pilot.pause()
        assert qv.current_file is None
