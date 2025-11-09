# CS2 Strafe Overlay

A lightweight, draggable WASD overlay with strafe/shot feedback for Counter‑Strike 2.
Global hooks via `pynput`, UI via Tkinter.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/run_overlay.py
```

## Install as package (editable)

```bash
pip install -e .
cs2-overlay
```

### Hotkeys (global)
- **F6** — toggle overlay visibility
- **+ / =** — scale up
- **-** — scale down

Window position is saved to `config.json` after first run.
