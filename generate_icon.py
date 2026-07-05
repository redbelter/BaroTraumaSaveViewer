"""Generate a submarine icon for the Barotrauma Save Viewer."""
from PIL import Image, ImageDraw
import math, os

sizes = [16, 24, 32, 48, 64, 128, 256]
assets = os.path.join(os.getcwd(), "assets")
os.makedirs(assets, exist_ok=True)

for S in sizes:
    img = Image.new("RGBA", (S, S), (30, 30, 46, 255))
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2
    r = S / 256  # scale factor

    # Horizontal submarine, pointing right
    hull_w = int(48 * r)    # half-width
    hull_h = int(14 * r)    # half-height

    # Outer glow
    for i in range(3, 0, -1):
        a = int(50 * (i / 3))
        d.ellipse(
            [cx - hull_w - i * int(4*r), cy - hull_h - i * int(3*r),
             cx + hull_w + i * int(4*r), cy + hull_h + i * int(3*r)],
            fill=(137, 180, 250, a)
        )

    body = (137, 180, 250, 255)
    dark = (107, 114, 128, 200)

    # Main cylindrical hull
    d.ellipse([cx - hull_w, cy - hull_h, cx + hull_w, cy + hull_h], fill=body)

    # Front nose cap (slightly rounded)
    if r >= 0.12:
        d.ellipse(
            [cx + hull_w - int(4*r), cy - int(10*r),
             cx + hull_w + int(6*r), cy + int(10*r)],
            fill=body
        )

    # Conning tower / sail (center-top rectangle + rounded top)
    if r >= 0.09:
        sw = int(12 * r)
        sh = int(10 * r)
        sx = cx - int(6 * r) - sw // 2
        sy = cy - hull_h - sh
        d.rectangle([sx, sy, sx + sw, sy + sh], fill=body)
        if r >= 0.15:
            d.ellipse([sx - int(2*r), sy - int(3*r), sx + sw + int(2*r), sy + int(2*r)], fill=body)

    # Periscope (thin line from sail top)
    if r >= 0.15:
        pw = max(2, int(3 * r))
        ph = int(6 * r)
        px = cx - int(4*r)
        py = cy - hull_h - int(16*r)
        d.rectangle([px, py, px + pw, py + ph], fill=(180, 190, 220, 190))
        d.ellipse([px - 1, py - 2, px + pw + 1, py + 2], fill=(180, 190, 220, 190))

    # Rear vertical fin (top and bottom)
    fw = int(6 * r)
    fh_t = int(10 * r)
    fh_b = int(10 * r)
    fx = cx - hull_w + int(6 * r)
    d.rectangle([fx, cy - hull_h - fh_t, fx + fw, cy - hull_h], fill=body)
    d.rectangle([fx, cy + hull_h, fx + fw, cy + hull_h + fh_b], fill=body)

    # Propeller on the back
    if r >= 0.10:
        px = cx - hull_w - int(2*r)
        for ang in [120, 240]:
            rad = math.radians(ang)
            pl = int(6 * r)
            ex = px + int(pl * math.cos(rad))
            ey = cy + int(pl * math.sin(rad))
            d.line([(px, cy), (ex, ey)], fill=dark, width=max(1, int(2 * r)))

    # Hull highlight (thin lighter arc along top)
    if r >= 0.2:
        d.arc(
            [cx - hull_w, cy - int(8*r), cx + hull_w, cy + int(4*r)],
            200, 340, fill=(200, 220, 255, 80), width=max(1, int(2*r))
        )

    img.save(os.path.join(assets, f"icon_{S}.png"))

# Build ICO
imgs = [Image.open(os.path.join(assets, f"icon_{s}.png")) for s in sizes]
ico = os.path.join(assets, "app_icon.ico")
imgs[0].save(ico, format="ICO", sizes=[(im.size[0], im.size[1]) for im in imgs])
imgs[-1].save(os.path.join(assets, "app_icon.png"))
print(f"Saved {ico}")
