"""Executes members of Claude's computer_toolset_20260801 on the real desktop with pyautogui."""

import time

from .screen import Screen, image_block

# Claude's key names (xdotool style) -> pyautogui names.
KEY_ALIASES = {
    "return": "enter", "enter": "enter", "escape": "esc", "esc": "esc", "backspace": "backspace",
    "delete": "delete", "tab": "tab", "space": "space", "super": "win", "cmd": "command",
    "command": "command", "meta": "command", "ctrl": "ctrl", "control": "ctrl", "alt": "alt",
    "option": "option", "shift": "shift", "page_up": "pageup", "page_down": "pagedown",
    "pageup": "pageup", "pagedown": "pagedown", "home": "home", "end": "end",
    "up": "up", "down": "down", "left": "left", "right": "right",
}


def _keys(combo: str) -> list[str]:
    return [KEY_ALIASES.get(k.strip().lower(), k.strip().lower()) for k in combo.replace(" ", "+").split("+") if k]


class Computer:
    def __init__(self):
        import pyautogui

        pyautogui.FAILSAFE = True  # slam the mouse into a screen corner to abort
        pyautogui.PAUSE = 0.05
        self.gui = pyautogui
        self.screen = Screen()

    def _move(self, inp: dict, key: str = "coordinate"):
        if inp.get(key):
            x, y = self.screen.to_screen(*inp[key])
            self.gui.moveTo(x, y, duration=0.15)

    def _with_modifiers(self, inp: dict, action):
        mods = _keys(inp["text"]) if inp.get("text") else []
        for m in mods:
            self.gui.keyDown(m)
        try:
            action()
        finally:
            for m in reversed(mods):
                self.gui.keyUp(m)

    def run(self, name: str, inp: dict):
        """Run one member action. Returns a list of content blocks for the tool_result."""
        g = self.gui
        if name == "screenshot":
            return [image_block(self.screen.grab())]
        if name == "zoom":
            return [image_block(self.screen.grab_region(*inp["region"]))]
        if name in ("left_click", "right_click", "middle_click", "double_click", "triple_click"):
            self._move(inp)
            button = {"right_click": "right", "middle_click": "middle"}.get(name, "left")
            clicks = {"double_click": 2, "triple_click": 3}.get(name, 1)
            self._with_modifiers(inp, lambda: g.click(button=button, clicks=clicks, interval=0.08))
        elif name == "left_click_drag":
            self._move(inp, "start_coordinate")
            x, y = self.screen.to_screen(*inp["coordinate"])
            self._with_modifiers(inp, lambda: g.dragTo(x, y, duration=0.4, button="left"))
        elif name == "mouse_move":
            self._move(inp)
        elif name == "left_mouse_down":
            g.mouseDown()
        elif name == "left_mouse_up":
            g.mouseUp()
        elif name == "cursor_position":
            x, y = self.screen.to_sent(*g.position())
            return [{"type": "text", "text": f"[{x}, {y}]"}]
        elif name == "scroll":
            self._move(inp)
            amount = int(inp.get("scroll_amount", 3))
            direction = inp["scroll_direction"]
            if direction in ("up", "down"):
                clicks = amount * 100 if direction == "up" else -amount * 100
                self._with_modifiers(inp, lambda: g.scroll(clicks))
            else:
                clicks = amount * 100 if direction == "right" else -amount * 100
                self._with_modifiers(inp, lambda: g.hscroll(clicks))
        elif name == "type":
            g.write(inp["text"], interval=0.01) if inp["text"].isascii() else self._paste(inp["text"])
        elif name == "key":
            for _ in range(int(inp.get("repeat", 1))):
                g.hotkey(*_keys(inp["text"]))
        elif name == "hold_key":
            keys = _keys(inp["text"])
            for k in keys:
                g.keyDown(k)
            time.sleep(float(inp["duration"]))
            for k in reversed(keys):
                g.keyUp(k)
        elif name == "wait":
            time.sleep(float(inp.get("duration", 1)))
        else:
            raise ValueError(f"Unknown computer action: {name}")
        return [{"type": "text", "text": "OK"}]

    def _paste(self, text: str):
        """pyautogui.write can't type non-ASCII; go through the clipboard instead."""
        import platform

        import pyperclip

        pyperclip.copy(text)
        self.gui.hotkey("command" if platform.system() == "Darwin" else "ctrl", "v")
