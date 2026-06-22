---
name: transcript-processor
description: Clean up and structure a raw video transcript. Use when the user pastes or provides a messy YouTube/auto-caption transcript (with timestamps, rolling duplicate lines, VTT/SRT/json3 formatting, or broken mid-sentence wrapping) and wants it cleaned, de-duplicated, segmented into sentences or paragraphs, re-timestamped, or summarized. Trigger with phrases like "clean up this transcript", "fix these captions", "make this transcript readable", or "summarize this transcript". Runs offline with no network or extra packages.
---

# Transcript Processor

Turn a raw, messy transcript into clean readable text. Deterministic, stdlib-only,
no internet — safe for the Claude.ai code-execution sandbox on any egress setting.

## What it fixes
- Rolling auto-caption duplication (each line repeating the tail of the previous).
- Broken mid-sentence line wrapping → rebuilt sentences.
- Non-speech annotations: `[music]`, `(applause)`, `♪`, `[inaudible]`, etc.
- Mixed input formats: VTT, SRT, json3, `[HH:MM:SS]` bracketed, plain text (auto-detected).
- Timestamps re-attached at sentence granularity.

## How to run
```bash
python3 scripts/process_transcript.py INPUT [--mode MODE] [--summary N] [--out FILE]
cat transcript.txt | python3 scripts/process_transcript.py
```
Modes: `clean` (default), `timestamped`, `sentences`, `paragraphs`.

## Workflow for Claude
1. Write the user's raw transcript to `raw.txt`.
2. Run `process_transcript.py raw.txt --mode clean` for clean paragraphs.
3. Use `--mode timestamped` if user wants timestamps.
4. Summarize the cleaned output yourself — far better than `--summary` heuristic.

## Exit codes
`0` success · `1` empty or unparseable input.
