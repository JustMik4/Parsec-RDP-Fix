"""Small vector-drawn UI icons without external image assets."""

from __future__ import annotations

from PIL import Image, ImageDraw

SCALE = 4


def make_icon(kind: str, color: str, size: int = 20) -> Image.Image:
    width = size * SCALE
    image = Image.new("RGBA", (width, width), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = max(3, width // 11)
    pad = width // 5

    if kind == "sun":
        middle = width / 2
        radius = width * 0.19
        draw.ellipse(
            (middle - radius, middle - radius, middle + radius, middle + radius),
            outline=color,
            width=stroke,
        )
        for x0, y0, x1, y1 in (
            (0.5, 0.10, 0.5, 0.22),
            (0.5, 0.78, 0.5, 0.90),
            (0.1, 0.5, 0.22, 0.5),
            (0.78, 0.5, 0.90, 0.5),
            (0.215, 0.215, 0.30, 0.30),
            (0.70, 0.70, 0.785, 0.785),
            (0.215, 0.785, 0.30, 0.70),
            (0.70, 0.30, 0.785, 0.215),
        ):
            draw.line((x0 * width, y0 * width, x1 * width, y1 * width), fill=color, width=stroke)
    elif kind == "moon":
        draw.ellipse((pad, pad, width - pad, width - pad), fill=color)
        # A mask gives the crescent a clean, transparent inner edge.
        mask = Image.new("L", (width, width), 0)
        brush = ImageDraw.Draw(mask)
        brush.ellipse((pad, pad, width - pad, width - pad), fill=255)
        brush.ellipse((width * 0.38, width * 0.12, width * 0.89, width * 0.65), fill=0)
        image.putalpha(mask)
    elif kind == "warning":
        draw.polygon(
            [
                (width // 2, int(width * 0.10)),
                (int(width * 0.95), int(width * 0.88)),
                (int(width * 0.05), int(width * 0.88)),
            ],
            fill=color,
        )
        draw.rounded_rectangle(
            (int(width * 0.46), int(width * 0.34), int(width * 0.54), int(width * 0.64)),
            radius=stroke // 2,
            fill="#FFFFFF",
        )
        draw.ellipse(
            (int(width * 0.46), int(width * 0.72), int(width * 0.54), int(width * 0.80)), fill="#FFFFFF"
        )
    else:
        raise ValueError(f"Unknown icon: {kind}")

    return image
