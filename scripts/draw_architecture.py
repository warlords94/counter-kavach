"""Draw docs/architecture.png (12 components on one CPU machine) with Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1500, 1040
BOX_W, BOX_H = 400, 96
COLS = [110, 550, 990]
ROWS = [150, 300, 450, 600, 790]
INK, MUTED, LINE, FILL, ACCENT = "#1d1d1f", "#5f6368", "#9aa0a6", "#f6f7f9", "#1a73e8"


def font(size: int, bold: bool = False):
    names = (["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold
             else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for name in names:
        for base in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"):
            p = Path(base) / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


def box(d, col, row, title, sub, accent=False):
    x, y = COLS[col], ROWS[row]
    d.rounded_rectangle([x, y, x + BOX_W, y + BOX_H], radius=14, fill="#e8f0fe" if accent else "#ffffff",
                        outline=ACCENT if accent else LINE, width=3 if accent else 2)
    d.text((x + BOX_W / 2, y + 34), title, font=font(25, True), fill=INK, anchor="mm")
    d.text((x + BOX_W / 2, y + 68), sub, font=font(19), fill=MUTED, anchor="mm")


def arrow(d, pts):
    d.line(pts, fill=LINE, width=3, joint="curve")
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    if x0 == x1:
        s = 1 if y1 > y0 else -1
        d.polygon([(x1, y1), (x1 - 8, y1 - 14 * s), (x1 + 8, y1 - 14 * s)], fill=LINE)
    else:
        s = 1 if x1 > x0 else -1
        d.polygon([(x1, y1), (x1 - 14 * s, y1 - 8), (x1 - 14 * s, y1 + 8)], fill=LINE)


def cx(col):
    return COLS[col] + BOX_W // 2


def main() -> None:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((W / 2, 40), "Everything runs on the branch PC; no customer data leaves the counter",
           font=font(30, True), fill=INK, anchor="mm")
    d.rounded_rectangle([70, 80, W - 70, H - 60], radius=20, fill=FILL, outline="#dadce0", width=2)
    d.text((95, 110), "Branch PC · CPU only · no network calls", font=font(21, True), fill=MUTED, anchor="lm")

    box(d, 0, 0, "Transaction details", "entered by counter staff")
    box(d, 1, 0, "Customer answers", "Yes/No buttons, typed or spoken")
    box(d, 2, 0, "Notice photo (P1)", "optional, from phone")
    box(d, 0, 1, "Anomaly scorer", "amount, age, new payee, live call")
    box(d, 1, 1, "Speech to text", "faster-whisper small, int8")
    box(d, 2, 1, "Text extraction (P1)", "Tesseract OCR, eng + hin")
    box(d, 1, 2, "Red-flag rules", "answer rules + regex, Hi/En")
    box(d, 2, 2, "LLM analyzer", "Qwen3-4B GGUF via llama.cpp")
    box(d, 1, 3, "Score fusion", "weights + floors + overrides", accent=True)
    box(d, 0, 4, "Risk card + actions", "evidence, what to say")
    box(d, 1, 4, "Incident report", "Markdown + HTML export")
    box(d, 2, 4, "Audit log + metrics", "hash chain, latency, joules")

    for col in range(3):
        arrow(d, [(cx(col), ROWS[0] + BOX_H), (cx(col), ROWS[1])])
    bus_y = ROWS[1] + BOX_H + 26
    d.line([(cx(1), ROWS[1] + BOX_H), (cx(1), bus_y)], fill=LINE, width=3)
    d.line([(cx(2), ROWS[1] + BOX_H), (cx(2), bus_y)], fill=LINE, width=3)
    d.line([(cx(1), bus_y), (cx(2), bus_y)], fill=LINE, width=3)
    d.text(((cx(1) + cx(2)) / 2, bus_y - 14), "answers + notice text", font=font(18), fill=MUTED, anchor="mm")
    arrow(d, [(cx(1), bus_y), (cx(1), ROWS[2])])
    arrow(d, [(cx(2), bus_y), (cx(2), ROWS[2])])
    fy = ROWS[3] + BOX_H // 2
    arrow(d, [(cx(0), ROWS[1] + BOX_H), (cx(0), fy), (COLS[1], fy)])
    d.text((cx(0) + 70, (ROWS[1] + BOX_H + fy) / 2), "anomaly score", font=font(18), fill=MUTED, anchor="mm")
    arrow(d, [(cx(1), ROWS[2] + BOX_H), (cx(1), ROWS[3])])
    arrow(d, [(cx(2), ROWS[2] + BOX_H), (cx(2), fy), (COLS[1] + BOX_W, fy)])
    split_y = ROWS[3] + BOX_H + 45
    d.line([(cx(1), ROWS[3] + BOX_H), (cx(1), split_y)], fill=LINE, width=3)
    d.line([(cx(0), split_y), (cx(2), split_y)], fill=LINE, width=3)
    for col in range(3):
        arrow(d, [(cx(col), split_y), (cx(col), ROWS[4])])

    d.text((W / 2, H - 30), "Counter Kavach · 12 components in one Python process · Phase 2: Kompact AI Runtime "
           "behind the same LLMBackend interface", font=font(19), fill=MUTED, anchor="mm")
    out = ROOT / "docs" / "architecture.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
