#!/usr/bin/env python3
"""Extract a canonical 11-character YouTube video ID from a URL or ID."""
import argparse
import re
import sys
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PATH_RE = re.compile(r"/(?:shorts|embed|live|v)/([A-Za-z0-9_-]{11})(?:[/?#]|$)")


def detect_video_id(value: str) -> str:
    value = value.strip()
    if VIDEO_ID_RE.fullmatch(value):
        return value

    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/", 1)[0]
        if VIDEO_ID_RE.fullmatch(candidate):
            return candidate

    query_id = parse_qs(parsed.query).get("v", [None])[0]
    if query_id and VIDEO_ID_RE.fullmatch(query_id):
        return query_id

    match = PATH_RE.search(parsed.path)
    if match:
        return match.group(1)

    loose = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})", value)
    if loose:
        return loose.group(1)

    raise ValueError(f"Could not detect an 11-character YouTube video ID from: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("youtube_url_or_id")
    args = parser.parse_args()
    try:
        print(detect_video_id(args.youtube_url_or_id))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
