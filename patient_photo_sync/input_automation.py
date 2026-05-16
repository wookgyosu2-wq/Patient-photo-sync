"""Mouse, keyboard, and clipboard abstractions."""

from __future__ import annotations

import importlib.util
import ctypes
import time

if importlib.util.find_spec("pyautogui") is not None:
    import pyautogui
else:  # pragma: no cover - dependency absence
    pyautogui = None

if importlib.util.find_spec("pyperclip") is not None:
    import pyperclip
else:  # pragma: no cover - dependency absence
    pyperclip = None


class DesktopAutomation:
    """Small wrapper around automation libraries used by the app."""

    def __init__(self) -> None:
        if pyautogui is None:
            raise RuntimeError("pyautogui is required. Run: pip install -r requirements.txt")
        pyautogui.PAUSE = 0.02

    def mouse_position(self) -> tuple[int, int]:
        point = pyautogui.position()
        return int(point.x), int(point.y)

    def click(self, x: int, y: int) -> None:
        pyautogui.click(x=x, y=y)

    def press_and_release_mouse(self, x: int, y: int, hold_seconds: float = 0.1) -> None:
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        time.sleep(hold_seconds)
        pyautogui.mouseUp()

    def copy_hotkey(self) -> None:
        pyautogui.hotkey("ctrl", "c")

    def paste_hotkey(self) -> None:
        pyautogui.hotkey("ctrl", "v")

    def enter(self) -> None:
        pyautogui.press("enter")

    def type_text(self, text: str) -> None:
        pyautogui.write(text)

    def clear_clipboard(self) -> None:
        self.set_clipboard("")

    def set_clipboard(self, text: str) -> None:
        if pyperclip is None:
            raise RuntimeError("pyperclip is required. Run: pip install -r requirements.txt")
        pyperclip.copy(text)

    def get_clipboard(self) -> str:
        if pyperclip is None:
            raise RuntimeError("pyperclip is required. Run: pip install -r requirements.txt")
        return pyperclip.paste()

    def clipboard_sequence_number(self) -> int:
        """Return Windows clipboard sequence number, or 0 where unavailable."""

        if hasattr(ctypes, "windll"):
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        return 0

    def wait_clipboard_changed(self, previous_sequence: int, timeout_seconds: float = 3.0) -> bool:
        """Wait until the clipboard changes, including non-text image data."""

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            current_sequence = self.clipboard_sequence_number()
            if current_sequence and current_sequence != previous_sequence:
                return True
            if not current_sequence and self.get_clipboard():
                return True
            time.sleep(0.05)
        return False
