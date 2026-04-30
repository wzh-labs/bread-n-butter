#!/usr/bin/env python3
"""Convert a YouTube auto-captions .vtt file to clean plain text.

Usage:
    python3 clean_vtt.py <path/to/file.vtt> > out.txt
    cat file.vtt | python3 clean_vtt.py - > out.txt

YouTube auto-caption VTT cues use a rolling-window format: each cue's first
content line repeats the previous cue's final text, and the second line adds
the newly-spoken words wrapped in <00:00:00.000><c>...</c> timing tags. We
keep the last content line per cue, strip timing/formatting tags, and dedupe
consecutive duplicates.
"""
import re
import sys


_TIMING_TAG = re.compile(r"<\d{2}:\d{2}:\d{2}\.\d{3}>")
_C_TAG = re.compile(r"</?c[^>]*>")
_ANY_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


def clean_vtt(text: str) -> str:
    text = re.sub(r"^WEBVTT.*?(?:\n\n|\Z)", "", text, count=1, flags=re.DOTALL)

    out = []
    for cue in text.strip().split("\n\n"):
        lines = [l for l in cue.split("\n") if l.strip() and "-->" not in l]
        if not lines:
            continue
        line = lines[-1]
        line = _TIMING_TAG.sub("", line)
        line = _C_TAG.sub("", line)
        line = _ANY_TAG.sub("", line)
        line = _WHITESPACE.sub(" ", line).strip()
        if line:
            out.append(line)

    deduped = []
    for line in out:
        if not deduped or deduped[-1] != line:
            deduped.append(line)

    return " ".join(deduped) + "\n"


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] == "-":
        text = sys.stdin.read()
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    sys.stdout.write(clean_vtt(text))


if __name__ == "__main__":
    main()
