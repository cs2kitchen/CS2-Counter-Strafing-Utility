from __future__ import annotations

import json
import os
import tkinter as tk
from typing import Dict, Optional

from ..engine import Engine


class DraggableFrame(tk.Frame):
    def __init__(self, master: tk.Toplevel, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.master = master
        self._ox = 0
        self._oy = 0
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)

    def _on_press(self, e: tk.Event) -> None:
        self._ox, self._oy = e.x, e.y

    def _on_drag(self, e: tk.Event) -> None:
        x = self.master.winfo_pointerx() - self._ox
        y = self.master.winfo_pointery() - self._oy
        self.master.geometry(f"+{x}+{y}")


class KeyOverlay(tk.Toplevel):
    """Top‑most transparent WASD + status label + extras + score strip."""

    def __init__(self, parent: tk.Tk, engine: Engine, *, config_path: Optional[str] = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config_path = config_path

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        self.transparent_col = "#010203"
        self.configure(bg=self.transparent_col)
        self.attributes("-transparentcolor", self.transparent_col)

        self._load_position()

        self.container = tk.Frame(self, bg=self.transparent_col, bd=0, highlightthickness=0)
        self.container.pack(padx=8, pady=8, fill="both", expand=True)

        # WASD tiles
        self.labels: Dict[str, tk.Label] = {}
        key_font = ("Segoe UI", 20, "bold")
        for k in ["W", "A", "S", "D"]:
            lbl = tk.Label(
                self.container,
                text=k,
                font=key_font,
                width=4,
                height=2,
                bd=0,
                relief="flat",
                fg="#35c759",
                bg="#111111",
                highlightthickness=2,
                highlightbackground="#35c759",
                highlightcolor="#35c759",
            )
            self.labels[k] = lbl

        self.labels["W"].grid(row=0, column=1, padx=6, pady=4)
        self.labels["A"].grid(row=1, column=0, padx=6, pady=4)
        self.labels["S"].grid(row=1, column=1, padx=6, pady=4)
        self.labels["D"].grid(row=1, column=2, padx=6, pady=4)
        for i in range(3):
            self.container.grid_columnconfigure(i, weight=1)
        for i in range(3):
            self.container.grid_rowconfigure(i, weight=1)

        # message with subtle outline
        self.msg_bg = "#0a0a0a"
        self.strafe_label = tk.Label(self.container, text="", font=("Segoe UI", 16, "bold"), fg="#35c759", bg=self.msg_bg, anchor="center")
        self.strafe_outline = tk.Label(self.container, text="", font=("Segoe UI", 16, "bold"), fg="#000000", bg=self.msg_bg, anchor="center")
        self.strafe_outline.grid(row=2, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        self.strafe_label.grid(row=2, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        self.strafe_label.lift(self.strafe_outline)

        # extras (CTRL/SPACE/LMB/RMB/SCROLL)
        self.extra_states: Dict[str, bool] = {k: False for k in ["CTRL", "SPACE", "LMB", "RMB", "SCROLL"]}
        self.extra_labels: Dict[str, tk.Label] = {}
        extra = tk.Frame(self.container, bg=self.transparent_col, bd=0, highlightthickness=0)
        extra.grid(row=3, column=0, columnspan=3, pady=(8, 0), sticky="ew")
        ef = ("Segoe UI", 14, "bold")
        for k in ["CTRL", "SPACE", "LMB", "RMB", "SCROLL"]:
            lbl = tk.Label(extra, text=k, font=ef, width=max(5, len(k) + 1), height=2, bd=0, relief="flat",
                           fg="#666666", bg="#111111", highlightthickness=2, highlightbackground="#222222", highlightcolor="#222222")
            lbl.pack(side="left", padx=4)
            self.extra_labels[k] = lbl
        self._scroll_reset_id: Optional[str] = None

        # WASD physical states (for CTRL combos)
        self.wasd_states: Dict[str, bool] = {k: False for k in ["W", "A", "S", "D"]}

        # score strip
        self.score_history: list[str] = []
        self.scores_frame = tk.Frame(self.container, bg=self.msg_bg, bd=0, highlightthickness=0)
        self.scores_frame.grid(row=4, column=0, columnspan=3, pady=(4, 0), sticky="ew")
        self.score_labels: list[tk.Label] = []
        for i in range(10):
            lbl = tk.Label(self.scores_frame, text="●", font=("Segoe UI", 12), fg="#444444", bg=self.msg_bg, width=2, height=1)
            lbl.grid(row=0, column=i, padx=2, pady=1, sticky="nsew")
            self.scores_frame.grid_columnconfigure(i, weight=1)
            self.score_labels.append(lbl)

        # window drag anywhere
        self._ox = 0
        self._oy = 0
        self.bind("<ButtonPress-1>", self._on_window_press)
        self.bind("<B1-Motion>", self._on_window_drag)

        # periodic UI refresh
        self.after(16, self._update_ui)

    # ---- persistence / window ------------------------------------------

    def _load_position(self) -> None:
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    pos = (json.load(f) or {}).get("key_overlay_pos")
                if pos:
                    self.geometry(f"+{pos[0]}+{pos[1]}")
                    return
            except Exception:
                pass
        self.geometry("+200+200")

    def _save_position(self) -> None:
        if not self.config_path:
            return
        try:
            x, y = self.winfo_x(), self.winfo_y()
            cfg = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f) or {}
            cfg["key_overlay_pos"] = [x, y]
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def destroy(self) -> None:  # noqa: D401
        self._save_position()
        super().destroy()

    # ---- UI -------------------------------------------------------------

    def _update_ui(self) -> None:
        self.engine.refresh()
        colours = self.engine.compute_key_colours()
        cmap = {
            Engine.COLOUR_GREEN: "#35c759",
            Engine.COLOUR_RED: "#ff3b30",
            Engine.COLOUR_ORANGE: "#ff9500",
            Engine.COLOUR_PURPLE: "#9b59b6",
            Engine.COLOUR_INACTIVE: "#333333",
        }
        if self.extra_states.get("CTRL", False):
            for k in colours:
                if self.wasd_states.get(k, False):
                    colours[k] = Engine.COLOUR_GREEN
        for k, lbl in self.labels.items():
            col = colours.get(k, Engine.COLOUR_INACTIVE)
            fg = "#666666" if col == Engine.COLOUR_INACTIVE else cmap.get(col, "#555555")
            border = fg if col == Engine.COLOUR_INACTIVE else fg
            lbl.configure(fg=fg, bg="#111111", highlightbackground=border, highlightcolor=border, highlightthickness=2)

        for k, lbl in self.extra_labels.items():
            active = self.extra_states.get(k, False)
            fg = "#ff3b30" if active else "#666666"
            border = "#ff3b30" if active else "#222222"
            lbl.configure(fg=fg, bg="#111111", highlightbackground=border, highlightcolor=border, highlightthickness=2)
        self.after(16, self._update_ui)

    def show_strafe_info(self, text: str, kind: str) -> None:
        cmap = {
            "Perfect": "#35c759",
            "Good": "#35c759",
            "Slow": "#35c759",
            "Overlap": "#ff9500",
            "Bad": "#ff3b30",
            "Micro": "#9b59b6",
            "Bad rubberband": "#9b59b6",
        }
        if text:
            self.strafe_outline.configure(text=text, bg=self.msg_bg)
            self.strafe_label.configure(text=text, fg=cmap.get(kind, "#35c759"), bg=self.msg_bg)
            self.strafe_label.lift(self.strafe_outline)
            self.add_score(kind or "")
        else:
            self.strafe_outline.configure(text="", bg=self.transparent_col)
            self.strafe_label.configure(text="", bg=self.transparent_col)

    def hide_strafe_info(self) -> None:
        self.strafe_outline.configure(text="", bg=self.transparent_col)
        self.strafe_label.configure(text="", bg=self.transparent_col)

    def _on_window_press(self, e: tk.Event) -> None:
        self._ox, self._oy = e.x, e.y

    def _on_window_drag(self, e: tk.Event) -> None:
        px, py = self.winfo_pointerx(), self.winfo_pointery()
        self.geometry(f"+{px - self._ox}+{py - self._oy}")

    # extras --------------------------------------------------------------

    def set_extra_key_state(self, key: str, pressed: bool) -> None:
        if key in self.extra_states:
            self.extra_states[key] = pressed

    def trigger_scroll(self) -> None:
        self.set_extra_key_state("SCROLL", True)
        if self._scroll_reset_id is not None:
            try:
                self.after_cancel(self._scroll_reset_id)
            except Exception:
                pass
            self._scroll_reset_id = None
        def reset() -> None:
            self.set_extra_key_state("SCROLL", False)
            self._scroll_reset_id = None
        self._scroll_reset_id = self.after(200, reset)

    def set_wasd_state(self, key: str, pressed: bool) -> None:
        if key in self.wasd_states:
            self.wasd_states[key] = pressed

    def adjust_scale(self, delta: float) -> None:
        if not hasattr(self, "_scale"):
            self._scale = 1.0
        self._scale = max(0.5, min(self._scale + delta, 2.5))
        k_base, kw, kh = 20, 4, 2
        ef_base, eh = 14, 2
        for _, lbl in self.labels.items():
            lbl.configure(font=("Segoe UI", int(k_base * self._scale), "bold"), width=max(2, int(kw * self._scale)), height=max(1, int(kh * self._scale)))
        for k, lbl in self.extra_labels.items():
            ew = max(5, len(k) + 1)
            lbl.configure(font=("Segoe UI", int(ef_base * self._scale), "bold"), width=max(2, int(ew * self._scale)), height=max(1, int(eh * self._scale)))
        for lbl in self.score_labels:
            lbl.configure(font=("Segoe UI", int(12 * self._scale)))
        self.update_idletasks()

    def toggle_visibility(self) -> None:
        self.withdraw() if self.winfo_ismapped() else self.deiconify()

    # score ---------------------------------------------------------------

    def add_score(self, category: str) -> None:
        if not category:
            return
        self.score_history.append(category)
        if len(self.score_history) > 10:
            self.score_history = self.score_history[-10:]
        self._update_scoreboard()

    def _update_scoreboard(self) -> None:
        cmap = {
            "Perfect": "#35c759",
            "Good": "#35c759",
            "Slow": "#35c759",
            "Overlap": "#ff9500",
            "Bad": "#ff3b30",
            "Micro": "#9b59b6",
            "Bad rubberband": "#9b59b6",
        }
        history = self.score_history[-10:]
        padded = [None] * (10 - len(history)) + history
        for lbl, cat in zip(self.score_labels, padded):
            lbl.configure(fg=("#444444" if cat is None else cmap.get(cat, "#444444")))
