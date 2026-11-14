#!/usr/bin/env python3
"""Render a silent, local-only demo from the verified Sandbox TAP output."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "demo" / "near-receipt-guard-local-sandbox.mp4"
LOG = (ROOT / "test-output.txt").read_text()
TEST_SOURCE = (ROOT / "test" / "guard.test.js").read_text()
assert "# tests 7" in LOG and "# pass 7" in LOG and "# fail 0" in LOG
assert "assert.equal(signCalls, 0)" in TEST_SOURCE
TEST_LINES = [line.strip() for line in LOG.splitlines() if re.match(r"^\s+ok [1-6] - ", line)]
assert len(TEST_LINES) == 6

W, H = 1280, 720
BG = "#101722"
CARD = "#182330"
TERMINAL = "#0B111A"
TEXT = "#F3F6F8"
MUTED = "#A8B7C4"
CYAN = "#7DD5D7"
GREEN = "#8DE2B1"
RED = "#F3A59D"
BORDER = "#344556"
LATO = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def wrap(draw: ImageDraw.ImageDraw, words: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in words.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=face) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def para(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int,
         face: ImageFont.FreeTypeFont, fill: str, line_height: int) -> int:
    for line in wrap(draw, text, face, width):
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height
    return y


def base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 8), fill=CYAN)
    d.text((64, 34), "NEAR Receipt Guard", font=font(BOLD, 25), fill=TEXT)
    d.rounded_rectangle((905, 28, 1216, 72), radius=18, fill=CARD, outline=BORDER, width=1)
    d.text((927, 39), "LOCAL SANDBOX  ·  AI-ASSISTED", font=font(BOLD, 17), fill=CYAN)
    d.line((64, 671, 1216, 671), fill=BORDER, width=1)
    d.text((64, 685), "Simulated NEAR only  ·  No mainnet transaction", font=font(LATO, 18), fill=MUTED)
    return im, d


def title_slide() -> Image.Image:
    im, d = base()
    d.text((64, 170), "An agent payment", font=font(BOLD, 74), fill=TEXT)
    d.text((64, 254), "with enforceable limits", font=font(BOLD, 74), fill=CYAN)
    para(d, "A Rust NEAR contract and a trusted preflight wrapper, tested end to end on a local blockchain.",
         68, 390, 1090, font(LATO, 33), MUTED, 45)
    for x, w, label in [(64, 295, "Scoped function-call key"),
                        (377, 226, "Contract policy"),
                        (621, 245, "One-time receipt")]:
        d.rounded_rectangle((x, 540, x + w, 592), radius=16, fill=CARD, outline=BORDER)
        d.text((x + 18, 552), label, font=font(BOLD, 22), fill=TEXT)
    return im


def architecture_slide() -> Image.Image:
    im, d = base()
    d.text((64, 112), "Two checks for each payment", font=font(BOLD, 54), fill=TEXT)
    d.text((66, 184), "The agent controls proposal data; the key and policy stay outside the prompt.",
           font=font(LATO, 27), fill=MUTED)
    for x in (64, 666):
        d.rounded_rectangle((x, 255, x + 550, 545), radius=24, fill=CARD, outline=BORDER, width=2)
    d.text((94, 285), "1  Before signing", font=font(BOLD, 34), fill=CYAN)
    para(d, "A SHA-256 receipt binds the exact contract, method, receiver, amount, and nonce. A changed proposal never reaches the signer.",
         94, 357, 485, font(LATO, 29), TEXT, 38)
    d.text((696, 285), "2  On the NEAR contract", font=font(BOLD, 34), fill=CYAN)
    para(d, "A function-call key can invoke execute only. The contract checks the receiver, per-call and daily caps, and nonce replay.",
         696, 357, 485, font(LATO, 29), TEXT, 38)
    d.text((625, 375), "→", font=font(BOLD, 45), fill=CYAN)
    d.text((84, 585), "proposal   →   receipt   →   scoped key   →   execute   →   recipient",
           font=font(MONO, 24), fill=MUTED)
    return im


def results_slide() -> Image.Image:
    im, d = base()
    d.text((64, 105), "Actual Sandbox test output", font=font(BOLD, 54), fill=TEXT)
    d.text((66, 172), "Saved from the local run on November 13, 2026", font=font(LATO, 26), fill=MUTED)
    d.rounded_rectangle((64, 220, 1216, 629), radius=19, fill=TERMINAL, outline=BORDER, width=2)
    d.rounded_rectangle((64, 220, 1216, 266), radius=19, fill=CARD)
    d.rectangle((64, 247, 1216, 266), fill=CARD)
    d.text((88, 231), "$ ./scripts/test-local.sh", font=font(MONO, 19), fill=CYAN)
    lines = TEST_LINES + ["# tests 7", "# pass 7", "# fail 0"]
    y = 285
    for line in lines:
        fill = GREEN if line.startswith("ok ") or line.startswith("# pass") else TEXT
        if line.startswith("# fail"):
            fill = CYAN
        d.text((88, y), line, font=font(MONO, 20), fill=fill)
        y += 36
    return im


def mutation_slide() -> Image.Image:
    im, d = base()
    d.text((64, 105), "A changed recipient stops here", font=font(BOLD, 54), fill=TEXT)
    d.text((66, 174), "The preflight receipt no longer matches the agent's proposed payment.",
           font=font(LATO, 27), fill=MUTED)
    d.rounded_rectangle((64, 260, 566, 452), radius=22, fill=CARD, outline=CYAN, width=2)
    d.rounded_rectangle((714, 260, 1216, 452), radius=22, fill=CARD, outline=RED, width=2)
    d.text((94, 290), "Preflight", font=font(BOLD, 32), fill=CYAN)
    d.text((94, 347), "approved recipient", font=font(LATO, 32), fill=TEXT)
    d.text((744, 290), "Injected change", font=font(BOLD, 32), fill=RED)
    d.text((744, 347), "blocked recipient", font=font(LATO, 32), fill=TEXT)
    d.text((620, 331), "×", font=font(BOLD, 57), fill=RED)
    d.rounded_rectangle((64, 490, 1216, 620), radius=20, fill=TERMINAL, outline=BORDER)
    d.text((92, 512), "ok 4 - mutation is rejected before signer is invoked", font=font(MONO, 21), fill=GREEN)
    d.text((92, 558), "assert.equal(signCalls, 0);", font=font(MONO, 27), fill=TEXT)
    d.text((800, 560), "test/guard.test.js", font=font(MONO, 19), fill=MUTED)
    return im


def closing_slide() -> Image.Image:
    im, d = base()
    d.text((64, 133), "7 passed  ·  0 failed", font=font(BOLD, 76), fill=GREEN)
    items = [
        "Allowed payment moved 1 simulated NEAR with a scoped key.",
        "Contract rejected blocked recipients, caps, and nonce replay.",
        "Wrapper rejected a changed proposal before signing.",
    ]
    y = 299
    for item in items:
        d.ellipse((70, y + 11, 88, y + 29), fill=CYAN)
        y = para(d, item, 112, y, 1030, font(LATO, 30), TEXT, 39) + 25
    d.rounded_rectangle((64, 557, 1216, 628), radius=19, fill=CARD, outline=BORDER)
    d.text((88, 574), "Source and reproduction: README.md  ·  test-output.txt", font=font(MONO, 22), fill=CYAN)
    return im


def main() -> None:
    slides = [title_slide(), architecture_slide(), results_slide(), mutation_slide(), closing_slide()]
    durations = [6, 12, 16, 11, 9]
    with tempfile.TemporaryDirectory(prefix="demo-render-", dir=ROOT / "demo") as temporary:
        paths = []
        for index, slide in enumerate(slides):
            path = Path(temporary) / f"slide-{index}.png"
            slide.save(path)
            paths.append(path)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "warning", "-y"]
        for path, duration in zip(paths, durations):
            command += ["-loop", "1", "-framerate", "24", "-t", str(duration), "-i", str(path)]
        filters = [f"[{i}:v]fps=24,format=yuv420p,setsar=1,settb=AVTB,setpts=PTS-STARTPTS[v{i}]"
                   for i in range(len(paths))]
        previous = "v0"
        length = durations[0]
        for i in range(1, len(paths)):
            offset = length - 0.5
            filters.append(f"[{previous}][v{i}]xfade=transition=fade:duration=0.5:offset={offset}[x{i}]")
            previous = f"x{i}"
            length += durations[i] - 0.5
        command += ["-filter_complex", ";".join(filters), "-map", f"[{previous}]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-r", "24", "-threads", "2",
                    "-filter_complex_threads", "2", "-movflags", "+faststart",
                    "-an", str(OUTPUT)]
        subprocess.run(command, check=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
