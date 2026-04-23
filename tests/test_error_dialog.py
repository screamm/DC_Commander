"""Pilot-driven tests for the rich :class:`ErrorDialog`.

Exercises the UI wiring of the dialog: message display, retry / cancel
buttons, details toggle, and keyboard shortcuts (Escape, Enter, ``d``).

All tests use Textual's ``App.run_test()`` which runs the app
headlessly. The project's ``pytest.ini`` uses asyncio mode ``strict``,
so every async test is explicitly marked with ``@pytest.mark.asyncio``.
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from textual.app import App, ComposeResult
from textual.widgets import Static

from components.dialogs import ErrorDialog

# Apply pytest-asyncio marker to every async test in this module.
pytestmark = pytest.mark.asyncio


class _HostApp(App):
    """Minimal host app that pushes an ``ErrorDialog`` on mount.

    The dialog construction is parametrised via class attributes so each
    test can customise it. The most-recent ``on_close`` action is
    appended to ``received_actions`` for assertions.
    """

    def __init__(
        self,
        *,
        message: str = "Something broke",
        title: str = "Error",
        details: Optional[str] = None,
        allow_retry: bool = False,
        allow_cancel: bool = True,
    ) -> None:
        super().__init__()
        self._message = message
        self._title = title
        self._details = details
        self._allow_retry = allow_retry
        self._allow_cancel = allow_cancel
        self.received_actions: List[Optional[str]] = []

    def compose(self) -> ComposeResult:
        # App needs at least one widget to mount cleanly; a blank
        # placeholder suffices.
        yield Static("host")

    def on_mount(self) -> None:
        dialog = ErrorDialog(
            message=self._message,
            title=self._title,
            details=self._details,
            allow_retry=self._allow_retry,
            allow_cancel=self._allow_cancel,
            on_close=self._on_close,
        )
        self.push_screen(dialog)

    def _on_close(self, action: Optional[str]) -> None:
        self.received_actions.append(action)


# --- Content & layout ----------------------------------------------------


async def test_dialog_shows_message() -> None:
    """The user-facing message text must be visible in the dialog."""
    app = _HostApp(message="The disk is full.")
    async with app.run_test() as pilot:
        await pilot.pause()
        # Find the message widget by id.
        message_widget = app.screen.query_one("#error_message", Static)
        assert "The disk is full." in str(message_widget.render())


async def test_dialog_title_visible() -> None:
    app = _HostApp(title="Copy failed", message="nope")
    async with app.run_test() as pilot:
        await pilot.pause()
        # The title is the first Static with class dialog-title.
        titles = app.screen.query(".dialog-title")
        titles_text = " ".join(str(t.render()) for t in titles)
        assert "Copy failed" in titles_text


# --- Button actions ------------------------------------------------------


async def test_dialog_retry_button_dismisses_with_retry() -> None:
    app = _HostApp(message="boom", allow_retry=True, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        # The Retry button should exist.
        from textual.widgets import Button
        retry_btn = app.screen.query_one("#retry", Button)
        retry_btn.press()
        await pilot.pause()
    assert app.received_actions == ["retry"]


async def test_dialog_cancel_button_dismisses_with_cancel() -> None:
    app = _HostApp(message="boom", allow_retry=True, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Button
        cancel_btn = app.screen.query_one("#cancel", Button)
        cancel_btn.press()
        await pilot.pause()
    assert app.received_actions == ["cancel"]


async def test_ok_button_when_retry_not_allowed() -> None:
    """When retry is disabled, the single button should read 'OK' but
    still carry ``id='cancel'`` and dismiss with action ``"cancel"``."""
    app = _HostApp(message="boom", allow_retry=False, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Button
        btn = app.screen.query_one("#cancel", Button)
        # Label should be "OK" not "Cancel".
        assert str(btn.label) == "OK"
        btn.press()
        await pilot.pause()
    assert app.received_actions == ["cancel"]


# --- Details toggle ------------------------------------------------------


async def test_details_toggle_via_key() -> None:
    """Pressing ``d`` toggles the details panel visibility."""
    app = _HostApp(
        message="boom",
        details="Traceback (most recent call last):\n  ...\nValueError: x",
        allow_retry=True,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        details_widget = app.screen.query_one("#error_details", Static)
        # Hidden initially.
        assert "visible" not in details_widget.classes

        await pilot.press("d")
        await pilot.pause()
        assert "visible" in details_widget.classes

        # Toggle off again.
        await pilot.press("d")
        await pilot.pause()
        assert "visible" not in details_widget.classes


async def test_details_toggle_via_button() -> None:
    """Clicking the Details button should reveal the details panel."""
    app = _HostApp(
        message="boom",
        details="stack trace here",
        allow_retry=False,
    )
    async with app.run_test() as pilot:
        await pilot.pause()
        from textual.widgets import Button

        details_widget = app.screen.query_one("#error_details", Static)
        assert "visible" not in details_widget.classes

        toggle_btn = app.screen.query_one("#details_toggle", Button)
        toggle_btn.press()
        await pilot.pause()
        assert "visible" in details_widget.classes


async def test_no_details_button_when_no_details() -> None:
    """Without ``details`` the dialog must not render a Details button."""
    app = _HostApp(message="boom", details=None, allow_retry=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Query should return empty.
        matches = app.screen.query("#details_toggle")
        assert len(matches) == 0


# --- Keyboard shortcuts --------------------------------------------------


async def test_escape_cancels() -> None:
    app = _HostApp(message="boom", allow_retry=True, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.received_actions == ["cancel"]


async def test_enter_triggers_retry_when_available() -> None:
    app = _HostApp(message="boom", allow_retry=True, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert app.received_actions == ["retry"]


async def test_enter_triggers_cancel_when_retry_disabled() -> None:
    app = _HostApp(message="boom", allow_retry=False, allow_cancel=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert app.received_actions == ["cancel"]


# --- Backward compatibility ---------------------------------------------


async def test_backwards_compat_message_title_only() -> None:
    """Legacy positional signature ``ErrorDialog(message, title=...)``
    must still work: ``allow_cancel`` defaults to True, so the dialog
    must still be dismissable via Escape."""

    class LegacyApp(App):
        def __init__(self) -> None:
            super().__init__()
            self.closed_with: List[Optional[str]] = []

        def compose(self) -> ComposeResult:
            yield Static("host")

        def on_mount(self) -> None:
            # Note: using the OLD call style but with a keyword title.
            self.push_screen(
                ErrorDialog(
                    "legacy call",
                    title="Legacy",
                    on_close=self.closed_with.append,
                )
            )

    app = LegacyApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
    assert app.closed_with == ["cancel"]
