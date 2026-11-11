"""Image tools: converter, resize and compress."""
from io import BytesIO

from flask import request
from PIL import Image

MAX_IMAGES = 15


def register(app, ctx):
    UserError = ctx.UserError
    send_bytes = ctx.send_bytes
    pick_files, stem = ctx.pick_files, ctx.stem
    open_image, flatten = ctx.open_image, ctx.flatten
    zip_bytes, make_view = ctx.zip_bytes, ctx.make_view

    # -----------------------------
    # IMAGE TOOLS
    # -----------------------------
    def do_image_converter():
        files = pick_files(1, MAX_IMAGES, "Please choose at least one image.")
        fmt = request.form.get("format", "jpg")
        if fmt not in ("jpg", "png", "webp"):
            fmt = "jpg"
        items = []
        for f in files:
            img = open_image(f)
            buf = BytesIO()
            if fmt == "jpg":
                flatten(img).save(buf, "JPEG", quality=90, optimize=True)
                mime = "image/jpeg"
            elif fmt == "png":
                flatten(img, keep_alpha=True).save(buf, "PNG", optimize=True)
                mime = "image/png"
            else:
                flatten(img, keep_alpha=True).save(buf, "WEBP", quality=90)
                mime = "image/webp"
            items.append((f"{stem(f, 'image')}.{fmt}", buf.getvalue(), mime))
        if len(items) == 1:
            return send_bytes(items[0][1], items[0][0], items[0][2])
        return send_bytes(zip_bytes([(n, d) for n, d, _ in items]), "Toolify_Images.zip", "application/zip")

    def to_int(value):
        try:
            n = int(float(value))
            return n if n > 0 else None
        except (TypeError, ValueError):
            return None

    def jpeg_under(img, kb):
        """Lower JPEG quality (then size) until the file is under kb."""
        limit = kb * 1024
        current = img
        for _ in range(12):
            for q in (90, 75, 60, 45, 30, 20):
                buf = BytesIO()
                current.save(buf, "JPEG", quality=q, optimize=True)
                if buf.tell() <= limit:
                    return buf.getvalue()
            if min(current.size) < 150:
                break
            current = current.resize((int(current.width * 0.8), int(current.height * 0.8)), Image.LANCZOS)
        return buf.getvalue()

    def do_resize_compress():
        files = pick_files(1, MAX_IMAGES, "Please choose at least one image.")
        target_kb = to_int(request.form.get("target_kb"))
        width = to_int(request.form.get("width"))
        quality = to_int(request.form.get("quality")) or 75
        quality = min(max(quality, 20), 95)
        if width and width > 6000:
            raise UserError("Width is too large. Use 6000 pixels or less.")
        items = []
        for f in files:
            img = open_image(f)
            if width and img.width > width:
                img = img.resize((width, max(1, int(img.height * width / img.width))), Image.LANCZOS)
            keep_png = (not target_kb and f.filename.lower().endswith(".png")
                        and (img.mode in ("RGBA", "LA") or "transparency" in img.info))
            if keep_png:
                buf = BytesIO()
                flatten(img, keep_alpha=True).save(buf, "PNG", optimize=True)
                data, ext = buf.getvalue(), "png"
            elif target_kb:
                data, ext = jpeg_under(flatten(img), target_kb), "jpg"
            else:
                buf = BytesIO()
                flatten(img).save(buf, "JPEG", quality=quality, optimize=True)
                data, ext = buf.getvalue(), "jpg"
            items.append((f"{stem(f, 'image')}_small.{ext}", data))
        if len(items) == 1:
            n, d = items[0]
            return send_bytes(d, n, "image/png" if n.endswith(".png") else "image/jpeg")
        return send_bytes(zip_bytes(items), "Toolify_Images.zip", "application/zip")


    routes = [
        ("/image-converter", "image_converter", do_image_converter),
        ("/resize-compress-image", "resize_compress_image", do_resize_compress),
    ]
    for rule, key, processor in routes:
        app.add_url_rule(rule, key, make_view(key, processor), methods=["GET", "POST"])
