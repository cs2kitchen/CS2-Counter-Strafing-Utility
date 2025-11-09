from __future__ import annotations

import os
import sys
import tkinter as tk
from typing import Optional

from .engine import Engine
from .ui.key_overlay import KeyOverlay


def _config_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def run_app() -> None:
    # Import inside to keep package import light for non-runtime contexts
    try:
        from pynput import keyboard, mouse  # type: ignore
    except ImportError:
        print("Install pynput to run this overlay. pip install pynput")
        sys.exit(1)

    engine = Engine()

    root = tk.Tk()
    root.withdraw()

    ko = KeyOverlay(root, engine, config_path=_config_path())
    hide_after: dict[str, Optional[str]] = {"id": None}

    # ---------------------------- helpers --------------------------------
    def _normalized_key_name(k) -> Optional[str]:
        """
        Robustly derive a lowercased key name from pynput Key/KeyCode.
        This fixes cases where CTRL (or other modifiers) suppress key.char.
        """
        try:
            # Prefer explicit names for special keys (e.g., 'ctrl', 'space', 'f6', etc.)
            if hasattr(k, "name") and k.name:
                return str(k.name).lower()

            # Regular character keys (when not suppressed by modifiers)
            if hasattr(k, "char") and k.char:
                return str(k.char).lower()

            # Fallback: virtual-key code → chr → lower
            if hasattr(k, "vk") and k.vk is not None:
                # Windows letter VKs are 65–90; chr() + lower() gets us 'a'..'z'
                try:
                    return chr(int(k.vk)).lower()
                except Exception:
                    return None
        except Exception:
            return None
        return None

    def _is_wasd(name: Optional[str]) -> bool:
        return name in ("w", "a", "s", "d")

    # ---------------------------- keyboard --------------------------------
    def on_press(key):
        try:
            name = _normalized_key_name(key)

            # Overlay controls
            if name == "f6":
                ko.toggle_visibility()
                return

            # Scale controls (main row + numpad variants resolve to same names)
            ch = getattr(key, "char", None)
            if (ch == "+") or name in ("+", "plus", "add", "equal"):
                ko.adjust_scale(0.1)
                return
            if (ch == "-") or name in ("-", "minus", "subtract"):
                ko.adjust_scale(-0.1)
                return

            # Movement + extras
            if _is_wasd(name):
                engine.press_key(name.upper())
                ko.set_wasd_state(name.upper(), True)
            elif name in ("ctrl", "ctrl_l", "ctrl_r", "control", "control_l", "control_r"):
                ko.set_extra_key_state("CTRL", True)
            elif name in ("space", " "):
                ko.set_extra_key_state("SPACE", True)
        except Exception:
            # Never let listener crash; silent by design for overlay stability
            pass

    def on_release(key):
        try:
            name = _normalized_key_name(key)

            if _is_wasd(name):
                engine.release_key(name.upper())
                ko.set_wasd_state(name.upper(), False)
            elif name in ("ctrl", "ctrl_l", "ctrl_r", "control", "control_l", "control_r"):
                ko.set_extra_key_state("CTRL", False)
            elif name in ("space", " "):
                ko.set_extra_key_state("SPACE", False)
        except Exception:
            pass

    # ------------------------------ mouse ---------------------------------
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
                    ko.show_strafe_info(msg, kind)
                else:
                    ko.set_extra_key_state("LMB", False)

                    def delayed_hide():
                        ko.hide_strafe_info()
                        hide_after["id"] = None

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

    # Listeners
    k_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    k_listener.daemon = True
    k_listener.start()

    m_listener = mouse.Listener(on_click=on_click, on_scroll=on_scroll)
    m_listener.daemon = True
    m_listener.start()

    # Teardown
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
