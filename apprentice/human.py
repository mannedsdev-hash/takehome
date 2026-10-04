"""Talking to you while the agent is driving: always-on-top pop-ups, falling back to the terminal."""


def _tk_root():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def _beep():
    print("\a", end="", flush=True)


def ask_text(question: str, context: str = "") -> str:
    """Ask a free-text question. Returns '' if you cancel."""
    _beep()
    prompt = f"{context}\n\n{question}" if context else question
    try:
        from tkinter import simpledialog

        root = _tk_root()
        answer = simpledialog.askstring("Apprentice needs you", prompt, parent=root)
        root.destroy()
        return (answer or "").strip()
    except Exception:
        print(f"\n[Apprentice asks] {prompt}")
        return input("> ").strip()


def confirm(question: str) -> bool:
    _beep()
    try:
        from tkinter import messagebox

        root = _tk_root()
        ok = messagebox.askyesno("Apprentice: confirm", question, parent=root)
        root.destroy()
        return bool(ok)
    except Exception:
        print(f"\n[Apprentice confirm] {question}")
        return input("[y/N] > ").strip().lower() in ("y", "yes")
