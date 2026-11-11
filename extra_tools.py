"""
Toolify extra tools (loader + shared helpers).
Registered from app.py with register(app, safe_text, safe_filename).
The tools themselves live in pdf_tools.py, image_tools.py and bill_tool.py.
"""
from io import BytesIO
from datetime import datetime
from types import SimpleNamespace
import os
import zipfile

from flask import request, render_template, flash, send_file
from PIL import Image, ImageOps

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

from tool_pages import PAGES
import pdf_tools
import image_tools
import bill_tool


class UserError(Exception):
    """A problem the visitor can fix (wrong file, missing field...)."""


MAX_IMAGES = 15
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "bmp", "gif"}


def register(app, safe_text, safe_filename):
    def show(key, error=None):
        if error:
            flash(error, "danger")
        form = request.form if request.method == "POST" else {"date": datetime.now().strftime("%Y-%m-%d")}
        return render_template("tool_page.html", page=PAGES[key], form=form), (400 if error else 200)

    def send_bytes(data, filename, mimetype):
        return send_file(BytesIO(data), as_attachment=True, download_name=filename, mimetype=mimetype)

    def send_pdf(data, filename):
        return send_bytes(data, filename, "application/pdf")

    def pick_files(min_n=1, max_n=MAX_IMAGES, msg="Please choose a file."):
        files = [f for f in request.files.getlist("files") if f and f.filename]
        if len(files) < min_n:
            raise UserError(msg)
        if len(files) > max_n:
            raise UserError(f"You can upload up to {max_n} files at a time.")
        return files

    def stem(fs, default="file"):
        return safe_filename(os.path.splitext(fs.filename)[0], default)

    def open_pdf(fs, allow_locked=False):
        data = fs.read()
        if b"%PDF" not in data[:1024]:
            raise UserError(f"'{fs.filename}' is not a valid PDF file.")
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception:
            raise UserError(f"Could not read '{fs.filename}'. The file may be damaged.")
        if doc.needs_pass and not allow_locked:
            raise UserError(f"'{fs.filename}' is password protected. Use Unlock PDF first.")
        return doc, data

    def open_image(fs):
        ext = fs.filename.rsplit(".", 1)[-1].lower() if "." in fs.filename else ""
        if ext not in IMAGE_EXT:
            raise UserError(f"'{fs.filename}' is not a supported image. Use JPG, PNG or WEBP.")
        try:
            img = Image.open(fs.stream)
            img.draft("RGB", (4000, 4000))
            img = ImageOps.exif_transpose(img)
        except Exception:
            raise UserError(f"Could not read '{fs.filename}'. Try another image.")
        return img

    def flatten(img, keep_alpha=False):
        """Return an RGB image (white background) or RGBA if keep_alpha."""
        has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        if has_alpha and keep_alpha:
            return img.convert("RGBA")
        if has_alpha:
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[-1])
            return bg
        return img.convert("RGB")

    def zip_bytes(items):
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in items:
                z.writestr(name, data)
        return buf.getvalue()

    def make_view(key, processor):
        def view():
            if request.method == "POST":
                try:
                    return processor()
                except UserError as e:
                    return show(key, str(e))
                except Exception:
                    app.logger.exception("Tool %s failed", key)
                    return show(key, "Something went wrong while processing your file. Please try a different file.")
            return show(key)
        view.__name__ = key
        return view


    ctx = SimpleNamespace(
        UserError=UserError, show=show, send_bytes=send_bytes, send_pdf=send_pdf,
        pick_files=pick_files, stem=stem, open_pdf=open_pdf, open_image=open_image,
        flatten=flatten, zip_bytes=zip_bytes, make_view=make_view,
        safe_text=safe_text, safe_filename=safe_filename,
    )
    pdf_tools.register(app, ctx)
    image_tools.register(app, ctx)
    bill_tool.register(app, ctx)
