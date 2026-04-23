"""Regression tests for Bug 2: ConfigScreen InvalidSelectValueError.

ConfigScreen.compose() previously constructed ``Select`` widgets with
``options`` tuples in ``(value, label)`` order, but Textual's ``Select``
expects ``(label, value)`` order. When the initial ``value=`` argument (e.g.
``'name'``) was compared against the option values, it found only capitalised
labels ("Name", "Size", …) and raised
``InvalidSelectValueError('name')``.

Fix: corrected all three ``Select`` option lists to ``(label, value)`` order
so that the default config values ("name", "auto", etc.) are valid option
values.
"""
from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Unit tests — verify options tuples are in (label, value) order
# ---------------------------------------------------------------------------


def test_sort_options_value_is_lowercase_string() -> None:
    """The second element of each sort option must be the machine value."""
    # Import here so the test fails fast if there's a syntax error in the module.
    from components.config_screen import ConfigScreen  # noqa: F401

    import ast, inspect, textwrap

    src = inspect.getsource(ConfigScreen.compose)
    tree = ast.parse(textwrap.dedent(src))

    # Walk AST looking for the sort_options assignment inside compose
    found_correct = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "sort_options":
                    # node.value should be a List of Tuples
                    if isinstance(node.value, ast.List):
                        first_tuple = node.value.elts[0]
                        if isinstance(first_tuple, ast.Tuple):
                            label_node, value_node = first_tuple.elts[:2]
                            # label should start with uppercase
                            if isinstance(label_node, ast.Constant):
                                assert label_node.value[0].isupper(), (
                                    f"Expected label (first element) to be capitalised, "
                                    f"got {label_node.value!r}"
                                )
                            # value should be lowercase
                            if isinstance(value_node, ast.Constant):
                                assert value_node.value.islower(), (
                                    f"Expected value (second element) to be lowercase, "
                                    f"got {value_node.value!r}"
                                )
                            found_correct = True
    assert found_correct, "Could not locate sort_options assignment in ConfigScreen.compose"


def test_size_options_value_is_lowercase_string() -> None:
    """The second element of each size_option must be the machine value."""
    import ast, inspect, textwrap
    from components.config_screen import ConfigScreen  # noqa: F401

    src = inspect.getsource(ConfigScreen.compose)
    tree = ast.parse(textwrap.dedent(src))

    found_correct = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "size_options":
                    if isinstance(node.value, ast.List):
                        first_tuple = node.value.elts[0]
                        if isinstance(first_tuple, ast.Tuple):
                            label_node, value_node = first_tuple.elts[:2]
                            if isinstance(label_node, ast.Constant):
                                assert label_node.value[0].isupper(), (
                                    f"Expected label (first element) to be capitalised, "
                                    f"got {label_node.value!r}"
                                )
                            if isinstance(value_node, ast.Constant):
                                assert value_node.value.islower(), (
                                    f"Expected value (second element) to be lowercase, "
                                    f"got {value_node.value!r}"
                                )
                            found_correct = True
    assert found_correct, "Could not locate size_options assignment in ConfigScreen.compose"


# ---------------------------------------------------------------------------
# Integration test — ConfigScreen mounts without InvalidSelectValueError
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


async def test_config_screen_mounts_without_error(tmp_path: Path) -> None:
    """ConfigScreen must mount successfully with default config values."""
    from textual.app import App, ComposeResult
    from features.config_manager import ConfigManager
    from features.theme_manager import ThemeManager
    from components.config_screen import ConfigScreen

    config_path = str(tmp_path / "test_config.json")
    config_manager = ConfigManager(config_path)
    theme_manager = ThemeManager()

    class _Host(App):
        def compose(self) -> ComposeResult:
            return iter([])

        def on_mount(self) -> None:
            self.push_screen(
                ConfigScreen(
                    config_manager=config_manager,
                    theme_manager=theme_manager,
                )
            )

    app = _Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        # InvalidSelectValueError would have been raised before this point.
        assert isinstance(app.screen, ConfigScreen)
