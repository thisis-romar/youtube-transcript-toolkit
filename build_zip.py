#!/usr/bin/env python3
"""Build the youtube_mcp_plugin.zip archive.

Generates a self-contained FastMCP plugin that extracts screenshots from a
YouTube video at caller-supplied timestamps and compiles them, alongside recap
text, into a styled PDF report. Run this script from any machine to produce a
ready-to-distribute ``youtube_mcp_plugin.zip``.

Usage:
    python3 build_zip.py [output.zip]
"""

import os
import sys
import zipfile

# Define the project files and their contents.
FILES = {
    "mcp_server.py": '''import os
import cv2
import yt_dlp
from fastmcp import FastMCP
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

mcp = FastMCP("YouTube Video Timestamp & PDF Generator")


def timestamp_to_seconds(ts_str: str) -> int:
    parts = list(map(int, ts_str.split(":")))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


@mcp.tool()
def generate_timestamped_pdf(
    video_url: str,
    timestamps_and_claims: list[dict],
    output_pdf_name: str = "recap_with_screenshots.pdf",
) -> str:
    """
    Extracts screenshots at specific timestamps from a YouTube video
    and compiles them alongside recap text into a PDF report.
    """
    temp_dir = "temp_mcp_screenshots"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        ydl_opts = {"format": "bestvideo[ext=mp4]/best[ext=mp4]/best", "quiet": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info["url"]

        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            return "Error: Unable to open video stream."

        for item in timestamps_and_claims:
            ts = item.get("timestamp", "00:00")
            seconds = timestamp_to_seconds(ts)
            cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)

            ret, frame = cap.read()
            if ret:
                img_path = os.path.join(temp_dir, f"frame_{ts.replace(':', '_')}.jpg")
                cv2.imwrite(img_path, frame)
                item["image_path"] = img_path
            else:
                item["image_path"] = None

        cap.release()

        doc = SimpleDocTemplate(
            output_pdf_name,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#1A365D"))
        section_style = ParagraphStyle("SecTitle", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#2B6CB0"))
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#2D3748"))

        story = [
            Paragraph("YouTube Video Timestamped Recap", title_style),
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15),
        ]

        current_section = None
        for item in timestamps_and_claims:
            section = item.get("section", "Recap")
            if section != current_section:
                current_section = section
                story.append(Spacer(1, 10))
                story.append(Paragraph(current_section, section_style))
                story.append(Spacer(1, 5))

            text = f"<b>Timestamp [{item.get('timestamp', 'N/A')}]:</b> {item.get('text', '')}"
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 8))

            if item.get("image_path") and os.path.exists(item["image_path"]):
                story.append(Image(item["image_path"], width=450, height=253))
                story.append(Spacer(1, 15))

        doc.build(story)
        return f"Successfully created PDF recap at: {os.path.abspath(output_pdf_name)}"

    except Exception as e:
        return f"Error generating PDF: {str(e)}"


if __name__ == "__main__":
    mcp.run()
''',

    "requirements.txt": '''fastmcp
yt-dlp
opencv-python
reportlab
''',

    "claude_desktop_config.json": '''{
  "mcpServers": {
    "youtube-pdf-tool": {
      "command": "python",
      "args": [
        "path/to/mcp_server.py"
      ]
    }
  }
}
''',

    "README.md": '''# YouTube Video Timestamp & PDF Generator MCP Server

An MCP plugin that fetches direct YouTube video frames at specified timestamps
and compiles a PDF document with the screenshots and recap text.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python mcp_server.py
```

## Integrating with Claude Desktop

Add the contents of `claude_desktop_config.json` to your Claude Desktop
configuration file, updating the file path to point to your `mcp_server.py`.
''',
}


def create_zip_package(output_zip: str = "youtube_mcp_plugin.zip") -> str:
    """Write every entry in FILES into ``output_zip`` and return its path."""
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for filename, content in FILES.items():
            zipf.writestr(filename, content.strip() + "\n")
            print(f"Added {filename} to archive.")
    abspath = os.path.abspath(output_zip)
    print(f"\nCreated successfully: {abspath}")
    return abspath


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "youtube_mcp_plugin.zip"
    create_zip_package(target)
