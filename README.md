# CS2 Counter-Strafing overlay

A lightweight, draggable WASD overlay with strafe accuracy  feedback for Counter‑Strike 2.
Global hooks via `pynput`, UI via Tkinter.

## Disclosure
There is use of AI in this project. 
It is stupid to design the buttons yourself. A lot of errors and bugs were fixed using AI.
You can find full history of prompts on this URL
The url may or may not be updated at the time you read this

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
