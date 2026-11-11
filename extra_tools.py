"""
Toolify extra tools: PDF tools, image tools and the bill generator.
Registered into the Flask app from app.py with register(app, safe_text, safe_filename).
"""
from io import BytesIO
from datetime import datetime
import os
import zipfile

from flask import request, render_template, flash, send_file
from PIL import Image, ImageOps

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

from fpdf import FPDF


class UserError(Exception):
    """A problem the visitor can fix (wrong file, missing field...)."""


MAX_PDF_PAGES_TO_IMAGES = 30
MAX_SPLIT_PAGES = 100
MAX_IMAGES = 15
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "bmp", "gif"}

# -----------------------------
# PAGE TEXT AND FORM FIELDS
# -----------------------------
PAGES = {
    "merge_pdf": dict(
        title="Merge PDF Files Online (Free, No Signup)",
        h1="Merge PDF", icon="bi-layers",
        intro="Combine two or more PDF files into one PDF in the order you select them. Free, no signup.",
        accept=".pdf,application/pdf", multiple=True, file_label="Choose PDF files (2 or more)",
        file_help="Tip: select the files in the order you want them.",
        options=[], button="Merge & Download PDF",
        steps=["Select 2 or more PDF files.", "Tap Merge & Download PDF.", "Your merged PDF downloads instantly."],
        faqs=[("Is there a limit?", "Up to 15 files and 25 MB in total."),
              ("Are my files saved?", "No. They are processed in memory and sent back to you.")],
    ),
    "split_pdf": dict(
        title="Split PDF - Extract Pages Online (Free)",
        h1="Split PDF", icon="bi-scissors",
        intro="Extract the pages you need from a PDF, or split every page into its own file.",
        accept=".pdf,application/pdf", multiple=False, file_label="Choose a PDF file",
        options=[
            dict(name="mode", label="What do you want?", type="select", default="range",
                 choices=[("range", "Extract selected pages into one PDF"),
                          ("each", "Split every page into separate PDFs (ZIP)")]),
            dict(name="pages", label="Pages to extract", type="text", placeholder="Example: 1-3, 5, 8-10",
                 help="Only needed for 'Extract selected pages'."),
        ],
        button="Split & Download",
        steps=["Choose your PDF.", "Type the page numbers or pick 'every page'.", "Download your new PDF or ZIP."],
        faqs=[("How do I write the pages?", "Use commas and dashes, like 1-3, 5, 8-10."),
              ("Is there a page limit?", "Splitting every page works up to 100 pages.")],
    ),
    "compress_pdf": dict(
        title="Compress PDF Online - Reduce PDF Size (Free)",
        h1="Compress PDF", icon="bi-file-zip",
        intro="Reduce the size of a PDF so it is easy to upload or send on WhatsApp and email.",
        accept=".pdf,application/pdf", multiple=False, file_label="Choose a PDF file",
        options=[dict(name="level", label="Compression level", type="select", default="medium",
                      choices=[("light", "Light (best quality)"),
                               ("medium", "Medium (recommended)"),
                               ("strong", "Strong (smallest file)")])],
        button="Compress & Download",
        steps=["Choose your PDF.", "Pick a compression level.", "Download the smaller PDF."],
        faqs=[("Will quality drop?", "Medium keeps text sharp and reduces image size. Use Light if you want the best quality."),
              ("Why did my file not shrink much?", "PDFs that are mostly text are already small and cannot shrink much.")],
    ),
    "lock_pdf": dict(
        title="Lock PDF - Add Password to PDF Online (Free)",
        h1="Lock PDF", icon="bi-lock",
        intro="Protect your PDF with a password so only people who know it can open the file.",
        accept=".pdf,application/pdf", multiple=False, file_label="Choose a PDF file",
        options=[dict(name="password", label="Set a password", type="password", required=True,
                      help="At least 4 characters. Remember it, because we cannot recover it.")],
        button="Lock & Download PDF",
        steps=["Choose your PDF.", "Type a password.", "Download your protected PDF."],
        faqs=[("Do you store my password?", "No. The password is only used to lock your file and is not saved.")],
    ),
    "unlock_pdf": dict(
        title="Unlock PDF - Remove PDF Password Online (Free)",
        h1="Unlock PDF", icon="bi-unlock",
        intro="Remove the password from a PDF when you already know the password.",
        accept=".pdf,application/pdf", multiple=False, file_label="Choose a locked PDF",
        options=[dict(name="password", label="Current password", type="password", required=True)],
        note="You must know the password. This tool cannot crack or guess passwords. Use it only on files you own.",
        button="Unlock & Download PDF",
        steps=["Choose your locked PDF.", "Type its password.", "Download the unlocked PDF."],
        faqs=[("I forgot the password. Can you recover it?", "No. This tool only works if you know the password.")],
    ),
    "pdf_to_jpg": dict(
        title="PDF to JPG Converter Online (Free, No Signup)",
        h1="PDF to JPG", icon="bi-file-earmark-image",
        intro="Convert each page of a PDF into a JPG image. Many pages are downloaded as a ZIP.",
        accept=".pdf,application/pdf", multiple=False, file_label="Choose a PDF file",
        options=[dict(name="quality", label="Image quality", type="select", default="150",
                      choices=[("100", "Normal (smaller files)"), ("150", "Good (recommended)"), ("200", "High (larger files)")])],
        button="Convert & Download",
        steps=["Choose your PDF.", "Pick the image quality.", "Download the JPG (or a ZIP for many pages)."],
        faqs=[("How many pages can I convert?", "Up to 30 pages at a time."),
              ("What do I get for a multi-page PDF?", "A ZIP file with one JPG per page.")],
    ),
    "image_converter": dict(
        title="Image Converter - JPG, PNG, WEBP (Free Online)",
        h1="Image Converter", icon="bi-arrow-left-right",
        intro="Convert images between JPG, PNG and WEBP. Many images are downloaded as a ZIP.",
        accept="image/*", multiple=True, file_label="Choose images (up to 15)",
        options=[dict(name="format", label="Convert to", type="select", default="jpg",
                      choices=[("jpg", "JPG"), ("png", "PNG"), ("webp", "WEBP")])],
        button="Convert & Download",
        steps=["Choose your images.", "Pick the format you want.", "Download the converted image or ZIP."],
        faqs=[("Which format should I use?", "JPG for photos, PNG for logos or transparent images, WEBP for small web images.")],
    ),
    "resize_compress_image": dict(
        title="Resize & Compress Image to KB (Free Online)",
        h1="Resize & Compress Image", icon="bi-aspect-ratio",
        intro="Make an image smaller in size or to an exact KB limit. Useful for exam forms, job portals and uploads.",
        accept="image/*", multiple=True, file_label="Choose images (up to 15)",
        options=[
            dict(name="target_kb", label="Target size in KB (optional)", type="number", placeholder="Example: 50",
                 help="We will reduce the quality until the image is under this size."),
            dict(name="width", label="Max width in pixels (optional)", type="number", placeholder="Example: 800",
                 help="Height changes automatically so the image is not stretched."),
            dict(name="quality", label="Quality (used if no target size)", type="select", default="75",
                 choices=[("90", "High"), ("75", "Medium (recommended)"), ("50", "Low (smallest)")]),
        ],
        button="Resize & Download",
        steps=["Choose your images.", "Type a target KB or a width (or both).", "Download the smaller image."],
        faqs=[("How do I make a photo under 50 KB?", "Type 50 in Target size and tap the button."),
              ("Which format is the result?", "JPG, unless a PNG with transparency is resized without a KB target.")],
    ),
    "bill_generator": dict(
        title="Bill / Invoice Generator with GST (Free PDF)",
        h1="Bill / Invoice Generator", icon="bi-receipt",
        intro="Create a clean invoice PDF with items, GST and totals. Free, no signup.",
        accept=None, multiple=False,
        options=[
            dict(name="seller_name", label="Your / shop name", type="text", required=True),
            dict(name="seller_address", label="Your address and phone", type="textarea", rows=2),
            dict(name="seller_gst", label="Your GSTIN (optional)", type="text"),
            dict(name="buyer_name", label="Customer name", type="text", required=True),
            dict(name="buyer_address", label="Customer address (optional)", type="textarea", rows=2),
            dict(name="invoice_no", label="Invoice number", type="text", default="1001"),
            dict(name="date", label="Date", type="date"),
            dict(name="items", label="Items (one per line: item, quantity, rate)", type="textarea", rows=6, required=True,
                 placeholder="Notebook, 5, 40\nPen box, 2, 120", help="Example: Notebook, 5, 40"),
            dict(name="gst_percent", label="GST % (0 if none)", type="number", default="0"),
            dict(name="notes", label="Notes (optional)", type="textarea", rows=2, placeholder="Thank you for your business!"),
        ],
        button="Create Bill PDF",
        steps=["Fill in your details and the customer name.", "Add items, one per line.", "Download your invoice PDF."],
        faqs=[("Can I add GST?", "Yes. Type the GST percentage and it is added to the total."),
              ("Is my data stored?", "No. The invoice is created in memory and downloaded to you.")],
    ),
}


# -----------------------------
# HELPERS
# -----------------------------
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

    # -----------------------------
    # PDF TOOLS
    # -----------------------------
    def do_merge():
        files = pick_files(2, 15, "Please select at least 2 PDF files.")
        out = fitz.open()
        for f in files:
            doc, _ = open_pdf(f)
            out.insert_pdf(doc)
        return send_pdf(out.tobytes(garbage=3, deflate=True), "Toolify_Merged.pdf")

    def parse_pages(spec, total):
        pages = []
        for part in spec.replace(" ", "").split(","):
            if not part:
                continue
            try:
                if "-" in part:
                    a, b = part.split("-", 1)
                    start, end = int(a), int(b)
                else:
                    start = end = int(part)
            except ValueError:
                raise UserError("Pages look wrong. Use numbers like 1-3, 5, 8-10.")
            if start < 1 or end < start or end > total:
                raise UserError(f"Page numbers must be between 1 and {total}.")
            pages.extend(range(start - 1, end))
        if not pages:
            raise UserError("Please type the pages you want, like 1-3, 5.")
        return pages

    def do_split():
        f = pick_files(1, 1, "Please choose a PDF file.")[0]
        doc, _ = open_pdf(f)
        name = stem(f, "Document")
        if request.form.get("mode") == "each":
            if doc.page_count > MAX_SPLIT_PAGES:
                raise UserError(f"This PDF has {doc.page_count} pages. Splitting every page works up to {MAX_SPLIT_PAGES}.")
            items = []
            for i in range(doc.page_count):
                part = fitz.open()
                part.insert_pdf(doc, from_page=i, to_page=i)
                items.append((f"{name}_page_{i + 1}.pdf", part.tobytes(garbage=3, deflate=True)))
            return send_bytes(zip_bytes(items), f"{name}_pages.zip", "application/zip")
        pages = parse_pages(request.form.get("pages", ""), doc.page_count)
        doc.select(pages)
        return send_pdf(doc.tobytes(garbage=3, deflate=True), f"{name}_extracted.pdf")

    def do_compress():
        f = pick_files(1, 1, "Please choose a PDF file.")[0]
        doc, original = open_pdf(f)
        dpi, quality = {"light": (200, 80), "medium": (150, 65), "strong": (100, 45)}.get(
            request.form.get("level", "medium"), (150, 65))
        try:
            doc.rewrite_images(dpi_threshold=dpi + 30, dpi_target=dpi, quality=quality)
        except Exception:
            pass  # older PyMuPDF: still clean and deflate below
        out = doc.tobytes(garbage=4, deflate=True, clean=True)
        if len(out) >= len(original):
            out = original  # never return a bigger file
        return send_pdf(out, f"{stem(f, 'Document')}_compressed.pdf")

    def do_lock():
        f = pick_files(1, 1, "Please choose a PDF file.")[0]
        password = request.form.get("password", "")
        if len(password) < 4:
            raise UserError("Password must be at least 4 characters.")
        doc, _ = open_pdf(f)
        out = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password,
                          garbage=3, deflate=True)
        return send_pdf(out, f"{stem(f, 'Document')}_locked.pdf")

    def do_unlock():
        f = pick_files(1, 1, "Please choose a PDF file.")[0]
        password = request.form.get("password", "")
        doc, _ = open_pdf(f, allow_locked=True)
        if doc.needs_pass:
            if not doc.authenticate(password):
                raise UserError("Wrong password. Please try again.")
        elif not doc.is_encrypted:
            raise UserError("This PDF is not password protected.")
        out = doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE, garbage=3, deflate=True)
        return send_pdf(out, f"{stem(f, 'Document')}_unlocked.pdf")

    def do_pdf_to_jpg():
        f = pick_files(1, 1, "Please choose a PDF file.")[0]
        doc, _ = open_pdf(f)
        if doc.page_count > MAX_PDF_PAGES_TO_IMAGES:
            raise UserError(f"This PDF has {doc.page_count} pages. The limit is {MAX_PDF_PAGES_TO_IMAGES} pages at a time. Use Split PDF first.")
        try:
            dpi = int(request.form.get("quality", "150"))
        except ValueError:
            dpi = 150
        dpi = min(max(dpi, 72), 200)
        zoom = dpi / 72
        name = stem(f, "Document")
        items = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            items.append((f"{name}_page_{i + 1}.jpg", pix.tobytes("jpeg", jpg_quality=85)))
        if len(items) == 1:
            return send_bytes(items[0][1], items[0][0], "image/jpeg")
        return send_bytes(zip_bytes(items), f"{name}_images.zip", "application/zip")

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

