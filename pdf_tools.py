"""PDF tools: merge, split, compress, lock, unlock, PDF to JPG."""
from flask import request

try:
    import pymupdf as fitz
except ImportError:
    import fitz

MAX_PDF_PAGES_TO_IMAGES = 30
MAX_SPLIT_PAGES = 100


def register(app, ctx):
    UserError = ctx.UserError
    send_bytes, send_pdf = ctx.send_bytes, ctx.send_pdf
    pick_files, stem, open_pdf = ctx.pick_files, ctx.stem, ctx.open_pdf
    zip_bytes, make_view = ctx.zip_bytes, ctx.make_view

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


    routes = [
        ("/merge-pdf", "merge_pdf", do_merge),
        ("/split-pdf", "split_pdf", do_split),
        ("/compress-pdf", "compress_pdf", do_compress),
        ("/lock-pdf", "lock_pdf", do_lock),
        ("/unlock-pdf", "unlock_pdf", do_unlock),
        ("/pdf-to-jpg", "pdf_to_jpg", do_pdf_to_jpg),
    ]
    for rule, key, processor in routes:
        app.add_url_rule(rule, key, make_view(key, processor), methods=["GET", "POST"])
