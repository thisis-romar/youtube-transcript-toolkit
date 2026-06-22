#!/usr/bin/env python3
"""Write the stable metadata.json artifact for a transcript worker run."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

VALID_STATUSES = {
    "success",
    "no_captions",
    "rate_limited",
    "network_error",
    "auth_required",
    "tool_missing",
    "processing_error",
    "failed",
}


def write_metadata(path: Path, **values: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "video_id": values["video_id"],
        "source_url": values["source_url"],
        "lang": values["lang"],
        "fetch_runtime": values["fetch_runtime"],
        "tool": values["tool"],
        "status": values["status"],
        "created_at": values.get("created_at") or datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--fetch-runtime", default="github_actions")
    parser.add_argument("--tool", default="yt-dlp")
    parser.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    args = parser.parse_args()
    write_metadata(
        args.out,
        video_id=args.video_id,
        source_url=args.source_url,
        lang=args.lang,
        fetch_runtime=args.fetch_runtime,
        tool=args.tool,
        status=args.status,
    )


if __name__ == "__main__":
    main()
