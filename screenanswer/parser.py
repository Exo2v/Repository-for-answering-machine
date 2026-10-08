"""Parse the model's final answer and map it to a tray color.

Ported from the v1.7 `answer_tray.py` parser (proven behaviour): only an
explicit labelled ANSWER line is trusted, digits elsewhere in the response
never become the result, and ambiguity resolves to neutral (None).
"""

from __future__ import annotations

import re
from typing import Optional

# The grey state means ready, busy, no answer, or a completed fade.
NEUTRAL_RGB = (128, 128, 128)
OPTION_RGB = {
    1: (229, 57, 53),       # red
    2: (253, 216, 53),      # yellow
    3: (67, 160, 71),       # green
    4: (30, 136, 229),      # blue
}
OPTION_NAMES = {1: "red", 2: "yellow", 3: "green", 4: "blue", 0: "neutral"}

ANSWER_LINE_RE = re.compile(
    r"^\s*\*{0,2}\s*(?:(final|correct)\s+)?answer\s*\*{0,2}\s*"
    r"(?::|=|\bis\b)\s*\*{0,2}\s*(?:option\s*)?\(?([0-4A-D])\)?"
    r"\s*[.)]?\s*\*{0,2}\s*$",
    flags=re.IGNORECASE,
)
SHORT_ANSWER_RE = re.compile(
    r"(?:answer\s*[:=]?\s*)?(?:option\s*)?\(?([0-4A-D])\)?(?:[.)])?",
    flags=re.IGNORECASE,
)


def _option_position(value: str) -> Optional[int]:
    normalized = value.upper()
    if normalized in ("A", "1"):
        return 1
    if normalized in ("B", "2"):
        return 2
    if normalized in ("C", "3"):
        return 3
    if normalized in ("D", "4"):
        return 4
    return None


def parse_option(response_text: Optional[str]) -> Optional[int]:
    """Return the option position 1-4 from a reasoned response, else None.

    Only a labelled answer line is extracted from a longer solution, so digits
    in the question or derivation cannot accidentally become the tray result.
    Lettered A-D responses map to their 1-4 choice positions. A position of 0
    is expressed by the model as `ANSWER: 0` and parses as None (neutral).
    """
    if not response_text:
        return None
    text = response_text.strip()
    labeled_answers = []
    final_answers = []
    for line in text.splitlines():
        match = ANSWER_LINE_RE.fullmatch(line.strip())
        if not match:
            continue
        prefix, value = match.groups()
        pair = (bool(prefix and prefix.lower() == "final"), value)
        labeled_answers.append(pair)
        if pair[0]:
            final_answers.append(pair)
    candidates = final_answers or labeled_answers
    if candidates:
        positions = {_option_position(value) for _is_final, value in candidates}
        if len(positions) != 1:
            return None
        position = positions.pop()
        return position if position is not None else None

    # Keep compatibility with older or unusually terse model responses.
    match = SHORT_ANSWER_RE.fullmatch(text)
    if not match:
        return None
    value = match.group(1)
    position = _option_position(value)
    return position if position is not None else None


def result_rgb(position: Optional[int]) -> tuple:
    """Map a parsed position to the tray color; None/0 -> neutral grey."""
    if position in OPTION_RGB:
        return OPTION_RGB[position]
    return NEUTRAL_RGB
