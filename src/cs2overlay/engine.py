from __future__ import annotations

import time
from typing import Dict, Optional, Tuple


class Engine:
    """Core timing/state machine for WASD and simple shot classification.

    Times are milliseconds; I kept floats for precision and cast when needed.
    Remember this is accurate but not extremely precise.
    """

    # Tuning
    ACCURATE_TAP_MS = 88
    SETTLE_AFTER_RELEASE_MS = 215
    MAX_VELOCITY_MS = 1000
    OPPOSITE_ACCURATE_MIN_MS = 70
    OPPOSITE_ACCURATE_MAX_MS = 200
    OVERLAP_ACCURATE_MS = 200

    # Semantic colours
    COLOUR_GREEN = "green"
    COLOUR_RED = "red"
    COLOUR_ORANGE = "orange"
    COLOUR_INACTIVE = "inactive"
    COLOUR_PURPLE = "purple"

    def __init__(self) -> None:
        self.key_down: Dict[str, bool] = {k: False for k in ["W", "A", "S", "D"]}
        self.key_t_down: Dict[str, float] = {k: 0.0 for k in ["W", "A", "S", "D"]}
        self.key_t_up: Dict[str, float] = {k: 0.0 for k in ["W", "A", "S", "D"]}

        self.axis_state: Dict[str, Dict[str, Optional[object]]] = {
            "vert": {"dir": None, "t_start": None, "at_max": False},
            "hori": {"dir": None, "t_start": None, "at_max": False},
        }
        self.prev_axis_state: Dict[str, Dict[str, Optional[object]]] = {
            "vert": {"dir": None, "at_max": False, "release_time": 0.0},
            "hori": {"dir": None, "at_max": False, "release_time": 0.0},
        }

        self.overlap_start: Dict[Tuple[str, str], float] = {}
        self.last_movement_release: float = 0.0

        # Horizontal simplified state
        self.horiz_current_key: Optional[str] = None
        self.horiz_press_time = 0.0
        self.horiz_last_release_key: Optional[str] = None
        self.horiz_last_release_time = 0.0
        self.horiz_opp_press_time: Optional[float] = None
        self.horiz_both_down_start: Optional[float] = None

        # Vertical simplified state
        self.vert_current_key: Optional[str] = None
        self.vert_press_time = 0.0
        self.vert_last_release_key: Optional[str] = None
        self.vert_last_release_time = 0.0
        self.vert_opp_press_time: Optional[float] = None
        self.vert_both_down_start: Optional[float] = None

    # public API

    def press_key(self, key: str) -> None:
        if key not in self.key_down:
            return
        t = self._now()
        if not self.key_down[key]:
            self.key_down[key] = True
            self.key_t_down[key] = t
            if key in ("A", "D"):
                self._on_horiz_press(key)
                self._on_axis_press("hori", key)
            elif key in ("W", "S"):
                self._on_vert_press(key)
                self._on_axis_press("vert", key)
            # start overlap timer if opposite already held
            for other in ["W", "A", "S", "D"]:
                if other != key and self.key_down[other] and self._is_opposite(key, other):
                    pair = tuple(sorted((key, other)))
                    self.overlap_start.setdefault(pair, t)

    def release_key(self, key: str) -> None:
        if key not in self.key_down:
            return
        t = self._now()
        if self.key_down[key]:
            self.key_down[key] = False
            self.key_t_up[key] = t
            if key in ("W", "S"):
                self.last_movement_release = t
                self._on_axis_release("vert", key)
                self._on_vert_release(key)
            elif key in ("A", "D"):
                self.last_movement_release = t
                self._on_axis_release("hori", key)
                self._on_horiz_release(key)
            # clear overlaps involving this key
            for pair in [p for p in self.overlap_start if key in p]:
                self.overlap_start.pop(pair, None)

    def refresh(self) -> None:
        t = self._now()
        for axis in ("vert", "hori"):
            st = self.axis_state[axis]
            if st["dir"] is not None and st["t_start"] is not None:
                st["at_max"] = (t - st["t_start"]) >= self.MAX_VELOCITY_MS
            else:
                st["at_max"] = False

    def compute_key_colours(self) -> Dict[str, str]:
        return {k: self._compute_colour_for_key(k) for k in ["W", "A", "S", "D"]}

    def evaluate_shot_strafe(self) -> Optional[Tuple[str, float]]:
        now = self._now()

        def horiz() -> Optional[Tuple[str, float]]:
            if self.key_down.get("A") and self.key_down.get("D") and self.horiz_both_down_start is not None:
                return ("Overlap", now - self.horiz_both_down_start)
            if self.horiz_opp_press_time is not None:
                dt = now - self.horiz_opp_press_time
                if 70.0 <= dt <= 90.0:
                    return ("Perfect", dt)
                if 90.0 < dt <= 130.0:
                    return ("Good", dt - 70.0)
                if 130.0 < dt <= 200.0:
                    return ("Slow", dt - 70.0)
                if dt > 200.0:
                    return ("Bad rubberband", dt - 200.0)
                return ("Good", 0.0)  # < 70ms
            if self.horiz_current_key is not None:
                held = now - self.horiz_press_time
                return ("Micro", held) if held < self.ACCURATE_TAP_MS else ("Maybe Accurate", held)
            if self.horiz_last_release_key is not None:
                held = self.horiz_last_release_time - self.horiz_press_time
                return ("Micro", held) if held < self.ACCURATE_TAP_MS else ("Bad", held)
            return None

        def vert() -> Optional[Tuple[str, float]]:
            if self.key_down.get("W") and self.key_down.get("S") and self.vert_both_down_start is not None:
                return ("Overlap", now - self.vert_both_down_start)
            if self.vert_opp_press_time is not None:
                dt = now - self.vert_opp_press_time
                if 70.0 <= dt <= 90.0:
                    return ("Perfect", dt)
                if 90.0 < dt <= 130.0:
                    return ("Good", dt - 70.0)
                if 130.0 < dt <= 200.0:
                    return ("Slow", dt - 70.0)
                if dt > 200.0:
                    return ("Bad rubberband", dt - 200.0)
                return ("Good", 0.0)
            if self.vert_current_key is not None:
                held = now - self.vert_press_time
                return ("Micro", held) if held < self.ACCURATE_TAP_MS else ("Bad", held)
            if self.vert_last_release_key is not None:
                held = self.vert_last_release_time - self.vert_press_time
                return ("Micro", held) if held < self.ACCURATE_TAP_MS else ("Bad", held)
            return None

        h, v = horiz(), vert()
        def ok(r: Optional[Tuple[str, float]]) -> bool:
            return r is not None and r[0] not in ("Bad", "Micro")
        if ok(h):
            return h
        if ok(v):
            return v
        return h or v

    # internals 

    @staticmethod
    def _now() -> float:
        return time.time() * 1000.0

    def _on_axis_press(self, axis: str, key: str) -> None:
        st = self.axis_state[axis]
        prev = self.prev_axis_state[axis]
        keep_prev = prev["dir"] is not None and prev["at_max"] and self._is_opposite(prev["dir"], key)
        if not keep_prev:
            prev["dir"] = None
            prev["at_max"] = False
            prev["release_time"] = 0.0
        if st["dir"] is None:
            st["dir"] = key
            now = self._now()
            st["t_start"] = now if now > 0 else 1.0
            st["at_max"] = False

    def _on_axis_release(self, axis: str, key: str) -> None:
        st = self.axis_state[axis]
        if st["dir"] == key:
            prev = self.prev_axis_state[axis]
            prev["dir"] = st["dir"]
            prev["at_max"] = st["at_max"]
            prev["release_time"] = self._now()
            st["dir"] = None
            st["t_start"] = None
            st["at_max"] = False

    @staticmethod
    def _is_opposite(k1: str, k2: str) -> bool:
        return (k1, k2) in {("W", "S"), ("S", "W"), ("A", "D"), ("D", "A")}

    def _quick_tap_accurate(self) -> bool:
        t = self._now()
        return any(self.key_down[k] and (t - self.key_t_down[k]) < self.ACCURATE_TAP_MS for k in ["W", "A", "S", "D"])

    def _release_settle_accurate(self) -> bool:
        if any(self.key_down[k] for k in ["W", "A", "S", "D"]):
            return False
        if self.last_movement_release <= 0:
            return False
        return (self._now() - self.last_movement_release) >= self.SETTLE_AFTER_RELEASE_MS

    def _any_axis_at_max(self) -> bool:
        return bool(self.axis_state["vert"]["at_max"] or self.axis_state["hori"]["at_max"])

    def _opposite_window_ms(self) -> Optional[float]:
        t = self._now()

        v_st, prev_v = self.axis_state["vert"], self.prev_axis_state["vert"]
        if v_st["dir"] is not None:
            opp = "W" if v_st["dir"] == "S" else "S"
            if self.key_down.get(opp, False) and not self.key_down[v_st["dir"]]:
                return t - self.key_t_down[opp]
        if prev_v["dir"] is not None:
            opp = "W" if prev_v["dir"] == "S" else "S"
            if self.axis_state["vert"]["dir"] == opp and self.key_t_down[opp] >= prev_v["release_time"]:
                return t - self.key_t_down[opp]

        h_st, prev_h = self.axis_state["hori"], self.prev_axis_state["hori"]
        if h_st["dir"] is not None:
            opp = "A" if h_st["dir"] == "D" else "D"
            if self.key_down.get(opp, False) and not self.key_down[h_st["dir"]]:
                return t - self.key_t_down[opp]
        if prev_h["dir"] is not None:
            opp = "A" if prev_h["dir"] == "D" else "D"
            if self.axis_state["hori"]["dir"] == opp and self.key_t_down[opp] >= prev_h["release_time"]:
                return t - self.key_t_down[opp]

        pressed = [k for k in ["W", "A", "S", "D"] if self.key_down[k]]
        if len(pressed) == 2:
            vec = tuple(sorted(pressed))
            opp_map = {("A", "W"): ("D", "S"), ("D", "S"): ("A", "W"), ("A", "S"): ("D", "W"), ("D", "W"): ("A", "S")}
            if vec in opp_map and self._any_axis_at_max():
                opp_vec = opp_map[vec]
                original_vec = opp_map[opp_vec]
                if not any(self.key_down[k] for k in original_vec):
                    times = [t - self.key_t_down[k] for k in opp_vec if self.key_down[k]]
                    if times:
                        return min(times)
        return None

    def _overlap_elapsed_ms(self) -> Optional[float]:
        t = self._now()
        best = 0.0
        active = False
        for (k1, k2), ts in self.overlap_start.items():
            if self.key_down.get(k1) and self.key_down.get(k2):
                active = True
                best = max(best, t - ts)
        return best if active else None

    def _compute_colour_for_key(self, key: str) -> str:
        if not self.key_down[key]:
            return self.COLOUR_INACTIVE
        # fresh opposite overlap
        for (k1, k2), ts in self.overlap_start.items():
            if key in (k1, k2) and self.key_down.get(k1) and self.key_down.get(k2):
                return self.COLOUR_ORANGE if (self._now() - ts) < self.OVERLAP_ACCURATE_MS else self.COLOUR_GREEN
        if self._quick_tap_accurate() or self._release_settle_accurate():
            return self.COLOUR_GREEN
        opp_ms = self._opposite_window_ms()
        if opp_ms is not None:
            if self.OPPOSITE_ACCURATE_MIN_MS <= opp_ms <= self.OPPOSITE_ACCURATE_MAX_MS:
                return self.COLOUR_GREEN
            if opp_ms > self.OPPOSITE_ACCURATE_MAX_MS:
                return self.COLOUR_RED
        if (self._now() - self.key_t_down[key]) >= self.ACCURATE_TAP_MS:
            return self.COLOUR_RED
        # subtle purple: key recently released and axis idle
        if key in ("A", "D"):
            if self.horiz_last_release_key is not None and self.horiz_opp_press_time is None and self.horiz_current_key is None:
                return self.COLOUR_PURPLE
        if key in ("W", "S"):
            if self.vert_last_release_key is not None and self.vert_opp_press_time is None and self.vert_current_key is None:
                return self.COLOUR_PURPLE
        return self.COLOUR_GREEN

    # simplified horizontal/vertical trackers
    def _on_horiz_press(self, key: str) -> None:
        now = self._now()
        if self.horiz_current_key is None:
            if self.horiz_last_release_key is not None and self._is_opposite(self.horiz_last_release_key, key):
                self.horiz_opp_press_time = now
            self.horiz_current_key = key
            self.horiz_press_time = now
            self.horiz_both_down_start = None
            return
        if self._is_opposite(self.horiz_current_key, key):
            self.horiz_both_down_start = self.horiz_both_down_start or now
            return
        if key == self.horiz_current_key:
            self.horiz_press_time = now

    def _on_horiz_release(self, key: str) -> None:
        now = self._now()
        self.horiz_both_down_start = None
        if self.horiz_current_key == key:
            self.horiz_opp_press_time = None
            self.horiz_last_release_key = key
            self.horiz_last_release_time = now
            self.horiz_current_key = None
        elif self.horiz_opp_press_time is not None and self.horiz_last_release_key and self._is_opposite(self.horiz_last_release_key, key):
            self.horiz_opp_press_time = None

    def _on_vert_press(self, key: str) -> None:
        now = self._now()
        if self.vert_current_key is None:
            if self.vert_last_release_key is not None and self._is_opposite(self.vert_last_release_key, key):
                self.vert_opp_press_time = now
            self.vert_current_key = key
            self.vert_press_time = now
            self.vert_both_down_start = None
            return
        if self._is_opposite(self.vert_current_key, key):
            self.vert_both_down_start = self.vert_both_down_start or now
            return
        if key == self.vert_current_key:
            self.vert_press_time = now

    def _on_vert_release(self, key: str) -> None:
        now = self._now()
        self.vert_both_down_start = None
        if self.vert_current_key == key:
            self.vert_opp_press_time = None
            self.vert_last_release_key = key
            self.vert_last_release_time = now
            self.vert_current_key = None
        elif self.vert_opp_press_time is not None and self.vert_last_release_key and self._is_opposite(self.vert_last_release_key, key):
            self.vert_opp_press_time = None
