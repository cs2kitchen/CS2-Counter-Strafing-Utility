from __future__ import annotations

import os
import sys
import tkinter as tk
from typing import Optional

def _config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def run_app() -> None:
    try:
        from pynput import keyboard, mouse  # type: ignore
    except ImportError:
        print("Install pynput to run this overlay. pip install pynput")
        sys.exit(1)

    # Local imports after pynput import succeeds
    from .engine import Engine
    from .ui.key_overlay import KeyOverlay

    engine = Engine()

    root = tk.Tk()
    root.withdraw()

    ko = KeyOverlay(root, engine, config_path=_config_path())
    hide_after: dict[str, Optional[str]] = {"id": None}

    # --- robust key normalization ---------------------------------------
    # Works reliably even when CTRL is held (char/name may be None/control codes).
    VK_TO_LETTER = {
        65: "a",  # A
        68: "d",  # D
        83: "s",  # S
        87: "w",  # W
    }

    def normalize_key(k) -> Optional[str]:
        # Explicit special keys
        if isinstance(k, keyboard.Key):
            if k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                return "ctrl"
            if k is keyboard.Key.space:
                return "space"
            return None

        # KeyCode path (includes letters, may have modifiers held)
        if isinstance(k, keyboard.KeyCode):
            # Try virtual-key first (reliable under CTRL)
            vk = getattr(k, "vk", None)
            if isinstance(vk, int) and vk in VK_TO_LETTER:
                return VK_TO_LETTER[vk]

            # Fallback to char if available
            ch = getattr(k, "char", None)
            if ch:
                ch = ch.lower()
                if ch in ("w", "a", "s", "d"):
                    return ch
                if ch in ("+", "=",):
                    return "plus"
                if ch in ("-", "_",):
                    return "minus"
            return None

        # Some platforms/situations may expose name
        name = getattr(k, "name", None)
        if name:
            name = name.lower()
            if name in ("w", "a", "s", "d", "ctrl", "ctrl_l", "ctrl_r", "space"):
                return "ctrl" if name.startswith("ctrl") else name
            if name in ("plus", "add", "equal", "minus", "subtract"):
                return name
        return None

    # keyboard ------------------------------------------------------------
    def on_press(key):
        try:
            name = normalize_key(key)

            # overlay shortcuts (scale & toggle) — support with and without modifiers
            if name == "plus":
                ko.adjust_scale(0.1); return
            if name == "minus":
                ko.adjust_scale(-0.1); return

            # toggle visibility (F6) — keep existing logic using name fallback
            if hasattr(key, "char") and getattr(key, "char") and getattr(key, "char").lower() == 'f':
                pass  # do nothing; handled elsewhere if needed
            if getattr(key, "name", None) and str(getattr(key, "name")).lower() == "f6":
                ko.toggle_visibility(); return

            if name in ("w", "a", "s", "d"):
                engine.press_key(name.upper())
                ko.set_wasd_state(name.upper(), True)
                return
            if name == "ctrl":
                ko.set_extra_key_state("CTRL", True)
                return
            if name == "space":
                ko.set_extra_key_state("SPACE", True)
                return
        except Exception:
            # swallow to keep listener resilient
            pass

    def on_release(key):
        try:
            name = normalize_key(key)
            if name in ("w", "a", "s", "d"):
                engine.release_key(name.upper())
                ko.set_wasd_state(name.upper(), False)
                return
            if name == "ctrl":
                ko.set_extra_key_state("CTRL", False)
                return
            if name == "space":
                ko.set_extra_key_state("SPACE", False)
                return
        except Exception:
            pass

    # mouse ---------------------------------------------------------------
    def on_click(x, y, button, pressed):
        try:
            if button == mouse.Button.left:
                if pressed:
                    ko.set_extra_key_state("LMB", True)
                    result = engine.evaluate_shot_strafe()
                    if result is not None:
                        category, dur = result
                        ms = 0 if dur is None else int(dur)
                        if category == "Perfect":
                            msg, kind = "Perfect", "Perfect"
                        elif category == "Good":
                            msg, kind = ("Good" if ms <= 0 else f"Good {ms} ms"), "Good"
                        elif category == "Slow":
                            msg, kind = ("Slow" if ms <= 0 else f"Slow {ms} ms"), "Slow"
                        elif category == "Overlap":
                            msg, kind = f"Overlap {ms} ms", "Overlap"
                        elif category == "Bad rubberband":
                            msg, kind = f"Bad rubberband {ms} ms", "Bad rubberband"
                        elif category == "Micro":
                            msg, kind = f"Micro {ms} ms", "Micro"
                        else:
                            msg, kind = (f"Bad {ms} ms" if ms < 120 else "Bad"), "Bad"
                    else:
                        msg, kind = "", ""
                    # Note: direct UI call from listener thread; acceptable short-term.
                    ko.show_strafe_info(msg, kind)
                else:
                    ko.set_extra_key_state("LMB", False)
                    def delayed_hide():
                        ko.hide_strafe_info(); hide_after["id"] = None
                    if hide_after["id"] is not None:
                        try:
                            root.after_cancel(hide_after["id"])
                        except Exception:
                            pass
                    hide_after["id"] = root.after(1000, delayed_hide)
            elif button == mouse.Button.right:
                ko.set_extra_key_state("RMB", bool(pressed))
        except Exception:
            pass

    def on_scroll(x, y, dx, dy):
        try:
            ko.trigger_scroll()
        except Exception:
            pass

    k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    k_listener.daemon = True
    k_listener.start()

    m_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    m_listener.daemon = True
    m_listener.start()

    def on_close() -> None:
        try:
            k_listener.stop()
        except Exception:
            pass
        try:
            m_listener.stop()
        except Exception:
            pass
        ko.destroy()
        root.destroy()

    ko.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main() -> None:
    run_app()
