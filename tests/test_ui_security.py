"""Tests for src.core.ui_security — UI input validation layer.

These tests cover the thin UX-friendly wrapper around
``src.core.security`` used by ``InputDialog`` callsites. They verify:

- Happy-path acceptance of reasonable filenames / paths
- Rejection of empty, ``.`` / ``..``, path separators, null bytes,
  reserved Windows names, and over-long names
- Rejection of path-traversal payloads against an explicit ``base_dir``
- ``must_exist`` contract
- ``expanduser()`` integration
- A 100-payload fuzz suite of path-traversal / control-character /
  reserved-name combinations — every payload must be rejected.
"""

from __future__ import annotations

import os
import random
import string
from pathlib import Path

import pytest

from src.core.ui_security import (
    MAX_FILENAME_LENGTH,
    UIValidationError,
    validate_user_filename,
    validate_user_path,
)


# ---------------------------------------------------------------------------
# validate_user_filename — happy path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "file.txt",
        "my_folder",
        "report 2026",
        "中文",  # non-ASCII
        "hello-world",
        "a",  # single char
        "a" * MAX_FILENAME_LENGTH,  # exactly at limit
        "archive.tar.gz",
        "_hidden_start",
        "with.multiple.dots.ext",
    ],
)
def test_valid_names_accepted(name: str) -> None:
    assert validate_user_filename(name) == name


# ---------------------------------------------------------------------------
# validate_user_filename — reject cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", ["", "   ", "\t", "\n", " \t\n "])
def test_empty_rejected(empty: str) -> None:
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_filename(empty)
    assert "empty" in exc_info.value.user_message.lower()


def test_dot_rejected() -> None:
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_filename(".")
    assert (
        "'.'" in exc_info.value.user_message
        or "cannot be" in exc_info.value.user_message.lower()
    )


def test_dotdot_rejected() -> None:
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_filename("..")
    assert "cannot be" in exc_info.value.user_message.lower()


@pytest.mark.parametrize(
    "name",
    [
        "foo/bar",
        "foo\\bar",
        "/absolute",
        "..\\windows",
        "./relative",
        "sub/dir/file.txt",
    ],
)
def test_slash_rejected(name: str) -> None:
    with pytest.raises(UIValidationError):
        validate_user_filename(name)


def test_null_byte_rejected() -> None:
    with pytest.raises(UIValidationError):
        validate_user_filename("foo\0bar")


@pytest.mark.parametrize(
    "name",
    [
        "CON",
        "NUL",
        "PRN",
        "AUX",
        "COM1",
        "COM9",
        "LPT1",
        "LPT9",
    ],
)
def test_reserved_windows_names_rejected(name: str) -> None:
    """Reserved Windows device names are in
    :attr:`SecurityConfig.forbidden_filenames` and thus rejected by
    :func:`is_safe_filename` on every platform."""
    with pytest.raises(UIValidationError):
        validate_user_filename(name)


@pytest.mark.parametrize("char", ["<", ">", ":", '"', "|", "?", "*"])
def test_dangerous_chars_rejected(char: str) -> None:
    with pytest.raises(UIValidationError):
        validate_user_filename(f"file{char}name")


@pytest.mark.parametrize(
    "ctrl_ord", [0, 1, 7, 9, 10, 13, 27, 31]  # NUL, SOH, BEL, TAB, LF, CR, ESC, US
)
def test_control_chars_rejected(ctrl_ord: int) -> None:
    name = f"file{chr(ctrl_ord)}name"
    with pytest.raises(UIValidationError):
        validate_user_filename(name)


def test_too_long_rejected() -> None:
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_filename("a" * (MAX_FILENAME_LENGTH + 1))
    assert "too long" in exc_info.value.user_message.lower()


def test_user_message_is_short_single_line() -> None:
    """User-facing messages should be a single short line — they go on
    the top of an ``ErrorDialog`` where verbose text is distracting."""
    try:
        validate_user_filename("foo/bar")
    except UIValidationError as exc:
        assert "\n" not in exc.user_message
        assert len(exc.user_message) < 120


# ---------------------------------------------------------------------------
# validate_user_filename — fuzz suite
# ---------------------------------------------------------------------------


def _make_fuzz_payloads(n: int = 100, *, seed: int = 0x5150) -> list[str]:
    """Generate ``n`` deterministic fuzz payloads that are all
    provably-unsafe filenames.

    Each payload is guaranteed to contain at least one of:
    - a path separator (``/`` or ``\\``)
    - a null byte
    - a control character (ASCII < 32)
    - a Windows-dangerous character (``<>:"|?*``)
    - OR the payload equals exactly a reserved Windows device name
      (e.g. ``CON``, ``NUL``, ``COM1``) or is ``"."`` / ``".."``.

    Substring appearance of reserved names does NOT count as unsafe —
    ``PRNtastic`` is a legitimate filename, so we never include those.
    """
    rng = random.Random(seed)
    char_fragments = [
        "/",
        "\\",
        "\0",
        "\x01",
        "\x1f",
        "\n",
        "\r",
        "\t",
        "<",
        ">",
        ":",
        '"',
        "|",
        "?",
        "*",
    ]
    traversal_fragments = ["../", "..\\", "/..", "\\..", "../../"]
    reserved_whole_names = [
        "CON", "NUL", "PRN", "AUX",
        "COM1", "COM9", "LPT1", "LPT9",
        ".", "..",
    ]
    safe_chars = string.ascii_letters + string.digits

    def _is_confirmed_unsafe(s: str) -> bool:
        if s in reserved_whole_names or s == "":
            return True
        if any(c in s for c in "/\\<>:\"|?*\0"):
            return True
        if any(ord(c) < 32 for c in s):
            return True
        return False

    payloads: list[str] = []
    while len(payloads) < n:
        roll = rng.random()
        if roll < 0.2:
            # Exactly-reserved name.
            payload = rng.choice(reserved_whole_names)
        elif roll < 0.5:
            # Traversal-heavy payload.
            parts = [
                rng.choice(traversal_fragments)
                for _ in range(rng.randint(1, 3))
            ]
            if rng.random() < 0.5:
                parts.append("".join(rng.choices(safe_chars, k=rng.randint(0, 4))))
            payload = "".join(parts)
        else:
            # Control/dangerous char soup.
            parts = [
                rng.choice(char_fragments)
                for _ in range(rng.randint(1, 4))
            ]
            if rng.random() < 0.5:
                parts.insert(
                    rng.randint(0, len(parts)),
                    "".join(rng.choices(safe_chars, k=rng.randint(0, 4))),
                )
            payload = "".join(parts)

        if _is_confirmed_unsafe(payload):
            payloads.append(payload)
        # otherwise regenerate — keep the fuzz set honest
    return payloads


def test_fuzz_100_random_payloads() -> None:
    """Every generated payload must be rejected by
    :func:`validate_user_filename` — if any single payload slips
    through, we have a security gap."""
    payloads = _make_fuzz_payloads(100)
    assert len(payloads) == 100

    accepted: list[str] = []
    for payload in payloads:
        try:
            validate_user_filename(payload)
        except UIValidationError:
            continue
        accepted.append(payload)

    assert not accepted, (
        f"{len(accepted)} fuzz payloads slipped through validation: "
        f"{accepted[:5]!r}..."
    )


# ---------------------------------------------------------------------------
# validate_user_path — happy path
# ---------------------------------------------------------------------------


def test_absolute_safe_path_accepted(tmp_path: Path) -> None:
    result = validate_user_path(str(tmp_path))
    assert result == tmp_path.resolve()


def test_trailing_whitespace_stripped(tmp_path: Path) -> None:
    result = validate_user_path(f"  {tmp_path}  ")
    assert result == tmp_path.resolve()


def test_expanduser_tilde_works() -> None:
    """Leading ``~`` must be expanded to the user's home directory."""
    result = validate_user_path("~")
    assert result == Path("~").expanduser().resolve()


def test_returned_path_is_absolute(tmp_path: Path) -> None:
    # Create a file then pass a relative-style path via cwd.
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        (tmp_path / "child").mkdir()
        result = validate_user_path("child")
        assert result.is_absolute()
        assert result == (tmp_path / "child").resolve()
    finally:
        os.chdir(cwd)


# ---------------------------------------------------------------------------
# validate_user_path — reject cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", ["", "   ", "\t"])
def test_empty_path_rejected(empty: str) -> None:
    with pytest.raises(UIValidationError):
        validate_user_path(empty)


def test_null_byte_in_path_rejected() -> None:
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_path("foo\0bar")
    # Should NOT leak a raw Python "embedded null character" ValueError
    # to the user.
    assert "null" not in exc_info.value.user_message.lower() or (
        "invalid" in exc_info.value.user_message.lower()
    )


def test_path_traversal_rejected_with_base_dir(tmp_path: Path) -> None:
    """Attempting to escape ``base_dir`` via ``..`` must be rejected."""
    # tmp_path/.. is the parent of tmp_path; this is outside base_dir.
    attacker_path = str(tmp_path / ".." / "not_in_base")
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_path(attacker_path, base_dir=tmp_path)
    assert (
        "escapes" in exc_info.value.user_message.lower()
        or "not allowed" in exc_info.value.user_message.lower()
    )


def test_base_dir_containment_accepts_inside_path(tmp_path: Path) -> None:
    inner = tmp_path / "sub"
    inner.mkdir()
    result = validate_user_path(str(inner), base_dir=tmp_path)
    assert result == inner.resolve()


def test_must_exist_rejects_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(UIValidationError) as exc_info:
        validate_user_path(str(missing), must_exist=True)
    assert "exist" in exc_info.value.user_message.lower()


def test_must_exist_accepts_existing(tmp_path: Path) -> None:
    existing = tmp_path / "real"
    existing.mkdir()
    result = validate_user_path(str(existing), must_exist=True)
    assert result == existing.resolve()


def test_must_exist_false_accepts_missing(tmp_path: Path) -> None:
    """Without ``must_exist`` we accept not-yet-existing paths (useful
    for save-as dialogs)."""
    missing = tmp_path / "future_file.txt"
    result = validate_user_path(str(missing), must_exist=False)
    assert result == missing.resolve()


# ---------------------------------------------------------------------------
# UIValidationError shape
# ---------------------------------------------------------------------------


def test_ui_validation_error_carries_both_messages() -> None:
    err = UIValidationError("short user msg", "longer technical detail")
    assert err.user_message == "short user msg"
    assert err.technical_details == "longer technical detail"
    assert str(err) == "short user msg"


def test_ui_validation_error_technical_details_optional() -> None:
    err = UIValidationError("only user msg")
    assert err.user_message == "only user msg"
    assert err.technical_details == ""
