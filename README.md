# CS2 Counter-Strafing overlay

A lightweight, draggable WASD overlay with strafe accuracy feedback for Counter Strike 2.
Global hooks via `pynput`, UI via Tkinter.

## Disclosure
There is use of AI in this project. (UI mostly)
It is stupid to design the buttons/UI yourself for a project like this. 
A lot of errors and bugs were fixed using AI.
(Example: What error is this -> Describe it-> What is the fix? -> Fix it! -> Does it break something else? -> Can it affect other logic?)
One of the core bugs with +ctrl led to non detection of keys during press.
It was way more complicated than you might hope
It is fixed
Even Chatgpt failed to fix the bug (Use of AI is smart when you know what you are doing to save time)


## Game Logic
The tool divides your movement into various categories (see youtube video for more details)
    1. Perfect 
    2. Good
    3. Slow
    4. Overlap
    5. Bad
    6. Bad
    7. Bad
    9. Microstrafe
    10. Rubberband

Why 3 bad's ?
 1. Shooting when moving without opposite key press and original release is real bad
 2. If gap between last key press and opposite key press is high it can create bad habits making you slow. You are accurate but it's a bad habit.
 3. With most rifles a keypress of less than 88 ms leads to an accurate shot, however this accuracy doesn't become completely broken at 89 but it does get worse as your velocity increases.
    This means you can still be accurate but it is again a bad precedent.

Perfect, Good, Slow ?
You are accurate -> Strive for good, perfect is very mechanical and won't happen too often




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
- **F6**     toggle overlay visibility
- **+ / =**      scale up
- **-**     scale down

Window position is saved to `config.json` after first run.

## Installation
Make sure you have python installed 
Download the files to a directory
Open a Terminal there
Follow above listed Bash or Package solutions
