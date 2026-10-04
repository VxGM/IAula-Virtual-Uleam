from PIL import Image, ImageDraw


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.16), fill=(11, 111, 189, 255))
    cx, cy, rad = size * 0.46, size * 0.54, size * 0.30
    steps = max(12, int(rad))
    for i in range(steps, 0, -1):
        t = i / steps
        col = (
            int(255 * (1 - t) + 143 * t),
            int(255 * (1 - t) + 216 * t),
            int(255 * (1 - t) + 255 * t),
            255,
        )
        r = rad * t
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    d.ellipse(
        [cx - rad * 0.62, cy - rad * 0.82, cx - rad * 0.02, cy - rad * 0.22],
        fill=(255, 255, 255, 235),
    )
    bx, by, br = size * 0.73, size * 0.29, size * 0.115
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(150, 220, 255, 255),
              outline=(255, 255, 255, 255), width=max(1, int(size * 0.014)))
    hx, hy, hr = bx - br * 0.35, by - br * 0.35, br * 0.28
    d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 255, 255, 245))
    return img


base = draw(256)
base.save("iaula.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("packaging/iaula.ico listo")
