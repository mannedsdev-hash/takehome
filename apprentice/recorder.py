"""Watches you do a task: screenshots on every click, plus what you typed, copied and pasted.

Controls while recording:
  F8   add a note (e.g. "I always write this answer myself", "skip jobs that need a visa")
  F9   pause / resume (use it before typing passwords or anything private)
  F10  stop

Output: recordings/<task>/<stamp>/events.jsonl and frames/*.jpg. Recordings stay on this computer;
only the frames picked for learning are sent to Claude when you run `learn`.
"""

import json
import queue
import threading
import time
from pathlib import Path

from . import config
from .human import ask_text
from .memory import now_stamp, slugify
from .screen import Screen, mark_click

MODIFIERS = {"ctrl", "ctrl_l", "ctrl_r", "cmd", "cmd_l", "cmd_r", "alt", "alt_l", "alt_r", "alt_gr", "shift", "shift_l", "shift_r"}
IDLE_FRAME_SECONDS = 6.0


def _key_name(key) -> str:
    if hasattr(key, "char") and key.char is not None:
        return key.char
    return str(key).replace("Key.", "")


class Recorder:
    def __init__(self, task: str, out_dir: Path | None = None, record_typing: bool = True):
        self.out = out_dir or (config.RECORDINGS_DIR / slugify(task) / now_stamp())
        (self.out / "frames").mkdir(parents=True, exist_ok=True)
        self.task = task
        self.record_typing = record_typing
        self.events: queue.Queue = queue.Queue()
        self.paused = False
        self.stopped = threading.Event()
        self._mods: set[str] = set()
        self._typed: list[str] = []
        self._frame_no = 0
        self._log = open(self.out / "events.jsonl", "a", encoding="utf-8")

    # ----- listener callbacks (run on pynput threads; they only enqueue) -----

    def _on_click(self, x, y, button, pressed):
        if pressed and not self.paused:
            self.events.put(("click", {"x": x, "y": y, "button": str(button).replace("Button.", "")}))

    def _on_scroll(self, x, y, dx, dy):
        if not self.paused:
            self.events.put(("scroll", {"x": x, "y": y, "dx": dx, "dy": dy}))

    def _on_press(self, key):
        name = _key_name(key)
        if name == "f10":
            self.stopped.set()
            return False
        if name == "f9":
            self.paused = not self.paused
            self.events.put(("status", {"paused": self.paused}))
            return
        if name == "f8":
            self.events.put(("note_request", {}))
            return
        if self.paused:
            return
        if name in MODIFIERS:
            self._mods.add(name.split("_")[0])
            return
        if self._mods - {"shift"}:
            self.events.put(("hotkey", {"keys": "+".join(sorted(self._mods)) + "+" + name.lower()}))
        else:
            self.events.put(("key", {"key": name}))

    def _on_release(self, key):
        name = _key_name(key)
        if name in MODIFIERS:
            self._mods.discard(name.split("_")[0])

    # ----- main-thread processing -----

    def _write(self, kind: str, data: dict, frame: str | None = None):
        rec = {"t": round(time.time(), 2), "kind": kind, **data}
        if frame:
            rec["frame"] = frame
        self._log.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._log.flush()

    def _frame(self, screen: Screen, click_at: tuple[int, int] | None = None) -> str:
        img = screen.grab()
        if click_at:
            img = mark_click(img, *screen.to_sent(*click_at))
        self._frame_no += 1
        name = f"frames/{self._frame_no:04d}.jpg"
        img.save(self.out / name, "JPEG", quality=70)
        return name

    def _flush_typing(self):
        if self._typed:
            text = "".join(self._typed)
            self._typed.clear()
            self._write("typed", {"text": text if self.record_typing else f"<{len(text)} characters, not recorded>"})

    def _clipboard(self) -> str:
        try:
            import pyperclip

            return pyperclip.paste()[:4000]
        except Exception:
            return ""

    def run(self):
        """Block until F10 (or stop()) and write the recording. Returns the recording folder."""
        from pynput import keyboard, mouse

        screen = Screen()
        ml = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        kl = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        ml.start()
        kl.start()
        self._write("start", {"task": self.task, "screen": [screen.sent_w, screen.sent_h]}, self._frame(screen))
        last_frame = time.time()
        scroll_pending = None
        try:
            while not self.stopped.is_set():
                try:
                    kind, data = self.events.get(timeout=0.5)
                except queue.Empty:
                    if scroll_pending:
                        self._write("scroll", scroll_pending, self._frame(screen))
                        scroll_pending, last_frame = None, time.time()
                    elif not self.paused and time.time() - last_frame > IDLE_FRAME_SECONDS:
                        self._flush_typing()
                        self._write("idle", {}, self._frame(screen))
                        last_frame = time.time()
                    continue

                if kind == "key":
                    k = data["key"]
                    if len(k) == 1:
                        self._typed.append(k)
                    elif k == "space":
                        self._typed.append(" ")
                    elif k == "backspace" and self._typed:
                        self._typed.pop()
                    else:
                        self._flush_typing()
                        self._write("key", data, self._frame(screen) if k in ("enter", "tab") else None)
                    continue

                self._flush_typing()
                if kind == "click":
                    time.sleep(0.25)  # let the UI react so the frame shows the result of the click
                    self._write("click", data, self._frame(screen, (data["x"], data["y"])))
                elif kind == "scroll":
                    if scroll_pending:
                        scroll_pending["dy"] += data["dy"]
                        scroll_pending["dx"] += data["dx"]
                    else:
                        scroll_pending = dict(data)
                    continue
                elif kind == "hotkey":
                    keys = data["keys"]
                    if keys.endswith("+c") or keys.endswith("+x"):
                        time.sleep(0.15)
                        data["clipboard"] = self._clipboard()
                        self._write("copy", data)
                    elif keys.endswith("+v"):
                        data["clipboard"] = self._clipboard()
                        time.sleep(0.3)
                        self._write("paste", data, self._frame(screen))
                    else:
                        time.sleep(0.3)
                        self._write("hotkey", data, self._frame(screen))
                elif kind == "status":
                    print("  [paused]" if data["paused"] else "  [recording]")
                    self._write("status", data)
                elif kind == "note_request":
                    note = ask_text("Note for the agent (why you did this, a rule to follow, what to ask you next time):")
                    if note:
                        self._write("note", {"text": note}, self._frame(screen))
                last_frame = time.time()
        finally:
            self._flush_typing()
            self._write("stop", {}, self._frame(screen))
            ml.stop()
            kl.stop()
            self._log.close()
        return self.out

    def stop(self):
        self.stopped.set()


def load_recording(folder: Path) -> list[dict]:
    with open(folder / "events.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
