#!/usr/bin/env python3
"""
Transcript processor (stdlib only, no network).

Takes a raw YouTube-style transcript in any common shape and produces clean,
readable output: removes auto-caption rolling duplicates, rebuilds sentences,
normalizes timestamps, and optionally emits a naive extractive summary.

Designed to run inside a sandbox with NO internet and NO extra packages, and to
work the same as a local CLI.

Input formats (auto-detected): vtt, srt, json3, bracketed ([HH:MM:SS] text),
plain text. Read from a file, a positional path, or stdin.

Usage:
    python3 process_transcript.py [INPUT] [options]
    cat transcript.txt | python3 process_transcript.py

Options:
    --format {auto,vtt,srt,json3,bracketed,plain}   Default: auto
    --mode   {clean,paragraphs,timestamped,sentences}   Default: clean
    --gap SECONDS     Start a new paragraph when the pause exceeds this (default 4)
    --summary N       Also print a naive N-sentence extractive summary
    --out FILE        Write to FILE instead of stdout

Exit codes: 0 ok | 1 empty/unparseable input
"""
import argparse, json, re, sys


# ---------- parsing: each parser returns list[(start_seconds: float, text: str)] ----------

def _ts_to_sec(h, m, s, ms="0"):
    return int(h) * 3600 + int(m) * 60 + int(s) + int((ms or "0").ljust(3, "0")[:3]) / 1000.0


def parse_json3(raw):
    j = json.loads(raw)
    out = []
    for e in j.get("events", []):
        if "segs" not in e:
            continue
        text = "".join(s.get("utf8", "") for s in e["segs"]).replace("\n", " ").strip()
        if text:
            out.append((e.get("tStartMs", 0) / 1000.0, text))
    return out


def parse_vtt(raw):
    out = []
    cue_re = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->")
    lines = raw.splitlines()
    i, start = 0, None
    buf = []
    def flush():
        if start is not None and buf:
            txt = " ".join(buf).strip()
            # strip inline timing tags <00:00:01.234> and <c> styling
            txt = re.sub(r"<[^>]+>", "", txt).strip()
            if txt:
                out.append((start, txt))
    for line in lines:
        m = cue_re.search(line)
        if m:
            flush(); buf = []
            start = _ts_to_sec(*m.groups())
        elif line.strip() and not line.strip().isdigit() and "WEBVTT" not in line \
                and "-->" not in line and not line.startswith(("Kind:", "Language:", "NOTE")):
            buf.append(line.strip())
        elif not line.strip():
            flush(); buf = []; start = None
    flush()
    return out


def parse_srt(raw):
    out = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    cue_re = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})[.,](\d{1,3})\s*-->")
    for b in blocks:
        lines = b.splitlines()
        start, txt = None, []
        for ln in lines:
            m = cue_re.search(ln)
            if m:
                start = _ts_to_sec(*m.groups())
            elif ln.strip().isdigit() and start is None and not txt:
                continue  # index line
            elif ln.strip():
                txt.append(ln.strip())
        if start is not None and txt:
            out.append((start, " ".join(txt)))
    return out


def parse_bracketed(raw):
    out = []
    # [HH:MM:SS] text  or  [M:SS] text  or  [SS] text
    pat = re.compile(r"^\[(?:(\d{1,2}):)?(?:(\d{1,2}):)?(\d{1,2})\]\s*(.*)$")
    for line in raw.splitlines():
        m = pat.match(line.strip())
        if m:
            a, b, c, text = m.groups()
            parts = [p for p in (a, b, c) if p is not None]
            parts = ["0"] * (3 - len(parts)) + parts  # pad to H,M,S
            sec = _ts_to_sec(parts[0], parts[1], parts[2])
            if text.strip():
                out.append((sec, text.strip()))
        elif line.strip():
            out.append((out[-1][0] if out else 0.0, line.strip()))
    return out


def parse_plain(raw):
    # No timestamps: treat each non-empty line as a segment at t=0 increasing index.
    return [(float(i), ln.strip()) for i, ln in enumerate(raw.splitlines()) if ln.strip()]


_NONSPEECH = re.compile(
    r"[\[(]\s*(?:music|applause|laughter|laughs?|inaudible|crosstalk|silence|"
    r"noise|cheering|chuckles?|sighs?|coughs?|sound effects?|background music|"
    r"♪+)\s*[\])]",
    re.IGNORECASE,
)

def strip_nonspeech(text):
    """Remove caption annotations like [music], (applause), ♪ that aren't speech."""
    text = _NONSPEECH.sub("", text)
    text = text.replace("\u266a", "").replace("\u266b", "")  # bare ♪ ♫
    return re.sub(r"\s{2,}", " ", text).strip()


def detect_format(raw):
    s = raw.lstrip()
    if s.startswith("WEBVTT"):
        return "vtt"
    if s.startswith("{") and '"events"' in s[:2000]:
        return "json3"
    if "-->" in s and re.search(r"^\s*\d+\s*$", s, re.M):
        return "srt"
    if re.search(r"^\s*\[(\d{1,2}:)?\d{1,2}:\d{1,2}\]", s, re.M) or \
       re.search(r"^\s*\[\d{1,2}:\d{2}\]", s, re.M):
        return "bracketed"
    return "plain"


PARSERS = {"vtt": parse_vtt, "srt": parse_srt, "json3": parse_json3,
           "bracketed": parse_bracketed, "plain": parse_plain}


# ---------- dedup rolling overlaps ----------

def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def merge_words(segments):
    """Collapse YouTube auto-caption rolling duplication into one word stream.
    Returns (words: list[str], times: list[float])."""
    words, times, nwords = [], [], []
    for start, text in segments:
        toks = text.split()
        if not toks:
            continue
        ntoks = [_norm(t) for t in toks]
        max_k = min(len(nwords), len(ntoks))
        overlap = 0
        for k in range(max_k, 0, -1):
            if nwords[-k:] == ntoks[:k]:
                overlap = k
                break
        for t, n in zip(toks[overlap:], ntoks[overlap:]):
            words.append(t); nwords.append(n); times.append(start)
    return words, times


# ---------- sentence segmentation ----------

_ABBR = {"mr", "mrs", "ms", "dr", "vs", "etc", "eg", "ie", "no", "st", "jr", "sr"}

def to_sentences(words, times):
    """Group words into sentences; return list[(start_time, sentence)]."""
    sents, cur, cur_start = [], [], None
    for w, t in zip(words, times):
        if cur_start is None:
            cur_start = t
        cur.append(w)
        if re.search(r"[.!?]\"?$", w):
            base = _norm(w)
            if base not in _ABBR and not re.fullmatch(r"[a-z]", base):
                sents.append((cur_start, " ".join(cur)))
                cur, cur_start = [], None
    if cur:
        sents.append((cur_start if cur_start is not None else 0.0, " ".join(cur)))
    return sents


def fmt_ts(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------- output modes ----------

def render(sents, mode, gap):
    if mode == "sentences":
        return "\n".join(s for _, s in sents)
    if mode == "timestamped":
        return "\n".join(f"[{fmt_ts(t)}] {s}" for t, s in sents)
    # clean / paragraphs: break on long pauses, else every ~4 sentences
    paras, cur, last_t, count = [], [], None, 0
    for t, s in sents:
        if cur and ((last_t is not None and t - last_t > gap) or count >= 4):
            paras.append(" ".join(cur)); cur, count = [], 0
        cur.append(s); last_t = t; count += 1
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras)


def extractive_summary(sents, n):
    """Naive frequency-based extractive summary. Heuristic; not a substitute for
    a real LLM summary (which Claude does from the cleaned text)."""
    stop = set("the a an and or but if then is are was were be been being to of in "
               "on for with as at by it this that these those you your i we they he "
               "she them his her our not so do does did have has had will would can "
               "could just like right now one two".split())
    freq = {}
    for _, s in sents:
        for w in re.findall(r"[a-z']+", s.lower()):
            if w not in stop and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1
    scored = []
    for idx, (t, s) in enumerate(sents):
        words = re.findall(r"[a-z']+", s.lower())
        score = sum(freq.get(w, 0) for w in words) / (len(words) + 1)
        scored.append((score, idx, t, s))
    top = sorted(scored, reverse=True)[:max(1, n)]
    top.sort(key=lambda x: x[1])  # restore original order
    return "\n".join(f"- {s}" for _, _, _, s in top)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="File path, or omit/'-' for stdin")
    ap.add_argument("--format", default="auto",
                    choices=["auto", "vtt", "srt", "json3", "bracketed", "plain"])
    ap.add_argument("--mode", default="clean",
                    choices=["clean", "paragraphs", "timestamped", "sentences"])
    ap.add_argument("--gap", type=float, default=4.0)
    ap.add_argument("--summary", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.input and a.input != "-":
        raw = open(a.input, encoding="utf-8", errors="replace").read()
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        print("Empty input.", file=sys.stderr); sys.exit(1)

    fmt = a.format if a.format != "auto" else detect_format(raw)
    segments = PARSERS[fmt](raw)
    segments = [(t, strip_nonspeech(x)) for t, x in segments]
    segments = [(t, x) for t, x in segments if x]
    if not segments:
        print(f"No segments parsed (detected format: {fmt}).", file=sys.stderr); sys.exit(1)

    words, times = merge_words(segments)
    sents = to_sentences(words, times)
    body = render(sents, a.mode, a.gap)

    if a.summary:
        body += "\n\n## Summary (heuristic)\n" + extractive_summary(sents, a.summary)

    if a.out:
        open(a.out, "w", encoding="utf-8").write(body + "\n")
        print(f"Wrote {a.out} (format={fmt}, {len(sents)} sentences)", file=sys.stderr)
    else:
        sys.stdout.write(body + "\n")


if __name__ == "__main__":
    main()
