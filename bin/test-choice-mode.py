#!/usr/bin/env python3
"""Stupid TUI prompts to soak-test Xbox Choice Mode (R3) in Ghostty.

Keys (same as Choice Mode injects):
  ↑ / ↓     move highlight
  Enter     confirm / next
  Space     toggle (multi-select only)
  Esc       cancel current question

Usage (in Ghostty):
  /usr/bin/python3 bin/test-choice-mode.py
"""
from __future__ import annotations

import curses
from dataclasses import dataclass, field


@dataclass
class Question:
    title: str
    options: list[str]
    multi: bool = False
    selected: set[int] = field(default_factory=set)
    cursor: int = 0


QUESTIONS = [
    Question(
        title="Q1 (single) — favorite useless fruit?",
        options=["Banana", "Durian", "Invisible apple", "USB-C grape"],
    ),
    Question(
        title="Q2 (single) — best fake programming language?",
        options=["Whitespace++", "EmojiScript", "YAML 2 (real this time)", "RegEx as a Service"],
    ),
    Question(
        title="Q3 (multi) — pick ALL toppings for a debug pizza:",
        options=["Stack traces", "printf", "rubber duck", "more RAM", "blame git"],
        multi=True,
    ),
    Question(
        title="Q4 (single) — ship it?",
        options=["Ship", "Ship but rename to MVP", "Rewrite in Rust first", "Take a nap"],
    ),
]


def draw(stdscr: curses.window, q: Question, idx: int, total: int, status: str) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    stdscr.addstr(0, 0, f"Choice Mode soak test  ({idx + 1}/{total})")
    stdscr.addstr(1, 0, "R3 enter mode · stick↑↓ · A=Enter · B=Esc · Y=Space")
    stdscr.addstr(3, 0, q.title[: max(0, w - 1)])
    kind = "multi-select (Space toggles)" if q.multi else "single-select"
    stdscr.addstr(4, 0, f"[{kind}]  Esc cancels")

    for i, opt in enumerate(q.options):
        y = 6 + i
        if y >= h - 2:
            break
        mark = "[x]" if (q.multi and i in q.selected) else "[ ]" if q.multi else "   "
        prefix = "▶" if i == q.cursor else " "
        line = f" {prefix} {mark} {opt}"
        attr = curses.A_REVERSE if i == q.cursor else curses.A_NORMAL
        stdscr.addstr(y, 0, line[: max(0, w - 1)], attr)

    stdscr.addstr(h - 1, 0, status[: max(0, w - 1)])
    stdscr.refresh()


def run_question(stdscr: curses.window, q: Question, idx: int, total: int) -> str | list[str] | None:
    status = "waiting…"
    while True:
        draw(stdscr, q, idx, total, status)
        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            q.cursor = (q.cursor - 1) % len(q.options)
            status = "↑"
        elif ch in (curses.KEY_DOWN, ord("j")):
            q.cursor = (q.cursor + 1) % len(q.options)
            status = "↓"
        elif ch == ord(" ") and q.multi:
            if q.cursor in q.selected:
                q.selected.discard(q.cursor)
                status = f"untoggled {q.options[q.cursor]}"
            else:
                q.selected.add(q.cursor)
                status = f"toggled {q.options[q.cursor]}"
        elif ch in (curses.KEY_ENTER, 10, 13):
            if q.multi:
                if not q.selected:
                    status = "pick at least one with Space, then Enter"
                    continue
                return [q.options[i] for i in sorted(q.selected)]
            return q.options[q.cursor]
        elif ch == 27:  # Esc
            return None


def main(stdscr: curses.window) -> None:
    curses.curs_set(0)
    stdscr.keypad(True)
    answers: list[tuple[str, object]] = []
    for i, q in enumerate(QUESTIONS):
        ans = run_question(stdscr, q, i, len(QUESTIONS))
        if ans is None:
            answers.append((q.title, "<canceled>"))
            break
        answers.append((q.title, ans))

    stdscr.erase()
    stdscr.addstr(0, 0, "Done. Answers:")
    y = 2
    for title, ans in answers:
        stdscr.addstr(y, 0, f"- {title}")
        y += 1
        stdscr.addstr(y, 0, f"  → {ans}")
        y += 2
    stdscr.addstr(y + 1, 0, "Press any key to quit.")
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
