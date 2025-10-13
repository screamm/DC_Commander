"""Test script to verify F2 menu system integration."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from components.menu_screen import MenuScreen, MenuAction, MenuCategory


def test_menu_action():
    """Test MenuAction creation."""
    action = MenuAction(
        label="Test Action",
        key="T",
        action="test_action",
        enabled=True,
        separator_after=False
    )
    assert action.label == "Test Action"
    assert action.key == "T"
    assert action.action == "test_action"
    assert action.enabled is True
    print("[OK] MenuAction creation works")


def test_menu_category():
    """Test MenuCategory creation."""
    actions = [
        MenuAction("Action 1", "1", "action1"),
        MenuAction("Action 2", "2", "action2"),
    ]
    category = MenuCategory(title="Test Menu", actions=actions)
    assert category.title == "Test Menu"
    assert len(category.actions) == 2
    assert category.selected_index == 0
    print("[OK] MenuCategory creation works")


def test_menu_screen():
    """Test MenuScreen creation."""
    menu = MenuScreen(active_panel="left")
    assert menu.active_panel == "left"
    assert len(menu.categories) == 5  # Left, Files, Commands, Options, Right
    print("[OK] MenuScreen creation works")


def test_menu_structure():
    """Test menu structure and actions."""
    menu = MenuScreen(active_panel="left")

    # Test that all categories have actions
    for category in menu.categories:
        assert len(category.actions) > 0, f"Category {category.title} has no actions"

        # Test that all actions have required fields
        for action in category.actions:
            assert action.label, f"Action missing label in {category.title}"
            assert action.key, f"Action missing key in {category.title}"
            assert action.action, f"Action missing action in {category.title}"

    print("[OK] Menu structure is complete")

    # Print menu summary
    print("\nMenu Summary:")
    for category in menu.categories:
        print(f"  {category.title}: {len(category.actions)} actions")


if __name__ == "__main__":
    print("Testing F2 Menu System Integration\n")

    try:
        test_menu_action()
        test_menu_category()
        test_menu_screen()
        test_menu_structure()

        print("\n[SUCCESS] All tests passed!")
        print("\nMenu system is ready. Press F2 in the application to test.")

    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
