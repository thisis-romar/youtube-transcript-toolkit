#!/usr/bin/env python3
"""Download a YouTube video and extract frames at exact timestamps.

Method (validated against the current YouTube gating):
  1. Download a compact H.264 copy with yt-dlp, routed through the shared access
     layer (cookies + EJS solver + po_token provider). H.264 (avc1) is chosen so
     the static ffmpeg build decodes it without the AV1 segfault seen on some
     wheels; the download uses Python networking (not ffmpeg), which sidesteps
     the static-ffmpeg TLS crash on network input.
  2. Extract one frame per timestamp from the LOCAL file (ffmpeg never touches
     the network here, so it never segfaults).

Usage:
    python3 video_frames.py <url> --timestamps 0,6:00,32:30 --out-dir DIR [options]

Options:
    --timestamps LIST   Comma list of SS | MM:SS | HH:MM:SS marks (required).
    --out-dir DIR       Where frames land (default: ./frames).
    --height N          Max height for the download (default 480).
    --keep-video        Keep the downloaded file (default: delete after extract).
    --proxy / --cookies / --no-check-certs   Access overrides (see ytdlp_access).

Prints, one per line: `<timestamp_seconds>\t<frame_path>` for each captured frame.
Exit codes: 0 ok | 3 no video formats (blocked IP) | 4 yt-dlp/ffmpeg missing | 5 network/other
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ytdlp_access as access  # noqa: E402


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        print("ffmpeg not found (install ffmpeg or `pip install imageio-ffmpeg`)", file=sys.stderr)
        sys.exit(4)


def parse_ts(s: str) -> int:
    parts = [int(p) for p in s.strip().split(":")]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(f"bad timestamp: {s}")


def download(url, out_dir, height, proxy, cookies, ncc) -> str:
    access.require_ytdlp()
    tmpl = os.path.join(out_dir, "source.%(ext)s")
    # Frames need no audio → prefer video-only H.264 (no merge step); progressive
    # 18 (360p) is a reliable single-file fallback. H.264 avoids the AV1 segfault.
    fmt = (f"bestvideo[vcodec^=avc1][height<={height}]/"
           f"136/135/134/18/best[height<={height}]")
    cmd = access.ytdlp_cli() + [
        "-f", fmt, "--no-part", "--no-playlist", "-o", tmpl,
    ]
    cmd += access.common_cli_flags(proxy, cookies, ncc, player_client="web")
    cmd.append(url)
    with access.pot_provider():
        proc = subprocess.run(cmd, capture_output=True, text=True)
    hits = sorted(glob.glob(os.path.join(out_dir, "source.*")))
    if not hits:
        err = proc.stderr
        if "Only images are available" in err or "Requested format is not available" in err:
            print("No video formats offered — the IP is rate-limited (429). Add cookies "
                  "($YT_COOKIES) or a residential --proxy. See resources/unblocking-youtube.md.",
                  file=sys.stderr)
            sys.exit(3)
        sys.stderr.write(err)
        sys.exit(5)
    return hits[0]


def grab_frames(ff, video, timestamps, out_dir):
    results = []
    for i, sec in enumerate(timestamps, 1):
        out = os.path.join(out_dir, f"frame_{i:02d}_t{sec}.jpg")
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(sec),
                        "-i", video, "-frames:v", "1", "-q:v", "2", out],
                       stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            results.append((sec, out))
        else:
            print(f"[frames] miss at t={sec}s", file=sys.stderr)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--timestamps", required=True)
    ap.add_argument("--out-dir", default="frames")
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--keep-video", action="store_true")
    ap.add_argument("--proxy")
    ap.add_argument("--cookies")
    ap.add_argument("--no-check-certs", action="store_true")
    a = ap.parse_args()

    timestamps = [parse_ts(s) for s in a.timestamps.split(",") if s.strip()]
    if not timestamps:
        print("no timestamps given", file=sys.stderr); sys.exit(2)

    os.makedirs(a.out_dir, exist_ok=True)
    ff = ffmpeg_exe()
    proxy, cookies, ncc = access.resolve_credentials(a.proxy, a.cookies, a.no_check_certs)

    video = download(a.url, a.out_dir, a.height, proxy, cookies, ncc)
    frames = grab_frames(ff, video, timestamps, a.out_dir)
    if not a.keep_video:
        with __import__("contextlib").suppress(Exception):
            os.remove(video)

    if not frames:
        print("no frames captured", file=sys.stderr); sys.exit(5)
    for sec, path in frames:
        print(f"{sec}\t{path}")


if __name__ == "__main__":
    main()
