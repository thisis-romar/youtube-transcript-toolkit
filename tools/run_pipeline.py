#!/usr/bin/env python3
"""Run the transcript worker pipeline and write a stable artifact folder.

This command is intended for network-capable workers such as GitHub Actions,
VPSes, or Cloud Run jobs. ChatGPT should trigger this command indirectly and
then inspect the files it writes under outputs/.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from detect_video_id import detect_video_id
from write_metadata import write_metadata

ROOT = Path(__file__).resolve().parents[1]
FETCH_SCRIPT = ROOT / "plugins/youtube-transcript/skills/youtube-transcript/scripts/fetch_transcript.py"
PROCESS_SCRIPT = ROOT / "skills/transcript-processor/scripts/process_transcript.py"

STATUS_BY_EXIT = {
    0: "success",
    2: "no_captions",
    3: "rate_limited",
    4: "tool_missing",
    5: "network_error",
    6: "auth_required",
}


def run_logged(cmd: list[str], log_path: Path) -> int:
    with log_path.open("a", encoding="utf-8") as log:
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=log, stderr=subprocess.STDOUT)
        log.write(f"\n[exit_code] {proc.returncode}\n")
        return proc.returncode


def maybe_process(raw_path: Path, clean_path: Path, segments_path: Path, log_path: Path) -> int:
    clean_code = run_logged([sys.executable, str(PROCESS_SCRIPT), str(raw_path), "--mode", "clean", "--out", str(clean_path)], log_path)
    if clean_code != 0:
        return clean_code
    return run_logged([sys.executable, str(PROCESS_SCRIPT), str(raw_path), "--mode", "paragraphs", "--out", str(segments_path)], log_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("youtube_url")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--timestamps", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--proxy", default=os.environ.get("TRANSCRIPT_PROXY_URL"))
    parser.add_argument("--cookies", help="Path to a Netscape cookies.txt file")
    parser.add_argument("--no-check-certs", action="store_true")
    parser.add_argument("--outputs-dir", default="outputs")
    parser.add_argument("--fetch-runtime", default=os.environ.get("FETCH_RUNTIME", "local_worker"))
    parser.add_argument("--stage", choices=["fetch", "all"], default="all",
                        help="Run only the network fetch smoke-test stage, or the full fetch+process pipeline")
    args = parser.parse_args()

    video_id = detect_video_id(args.youtube_url)
    outputs = Path(args.outputs_dir)
    outputs.mkdir(parents=True, exist_ok=True)

    raw_json3 = outputs / f"{video_id}.raw.json3"
    raw = outputs / f"{video_id}.timestamped.txt"
    clean = outputs / f"{video_id}.clean.txt"
    segments = outputs / f"{video_id}.segments.md"
    metadata = outputs / f"{video_id}.metadata.json"
    log = outputs / f"{video_id}.fetch.log"
    exit_code_file = outputs / f"{video_id}.exit_code.txt"

    fetch_cmd = [sys.executable, str(FETCH_SCRIPT), args.youtube_url, "--lang", args.lang, "--out", str(raw), "--raw-out", str(raw_json3)]
    if args.timestamps:
        fetch_cmd.append("--timestamps")
    if args.proxy:
        fetch_cmd.extend(["--proxy", args.proxy])
    if args.cookies:
        fetch_cmd.extend(["--cookies", args.cookies])
    if args.no_check_certs:
        fetch_cmd.append("--no-check-certs")

    fetch_code = run_logged(fetch_cmd, log)
    status = STATUS_BY_EXIT.get(fetch_code, "network_error")
    final_code = fetch_code

    if fetch_code == 0 and args.stage == "all":
        process_code = maybe_process(raw, clean, segments, log)
        if process_code != 0:
            status = "processing_error"
            final_code = process_code

    exit_code_file.write_text(f"{final_code}\n", encoding="utf-8")
    write_metadata(
        metadata,
        video_id=video_id,
        source_url=args.youtube_url,
        lang=args.lang,
        fetch_runtime=args.fetch_runtime,
        tool="yt-dlp",
        status=status,
    )
    print(f"status={status}")
    print(f"outputs={outputs}")
    sys.exit(final_code)


if __name__ == "__main__":
    main()
