from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO
from PIL import Image, ImageOps
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "toolify-secret-key-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit


# -----------------------------
# HELPERS
# -----------------------------
# The built-in PDF fonts only support basic Latin characters.
# Without this, text like bullets (•), quotes (“ ”) or ₹ would crash the PDF.
REPLACEMENTS = {
    "•": "-", "–": "-", "—": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "₹": "Rs.", "\u00a0": " ", "\t": "    ",
}


def safe_text(text):
    text = text or ""
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def safe_filename(name, default="file"):
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", name.replace(" ", "_"))[:40]
    return cleaned or default


def pdf_to_buffer(pdf):
    buffer = BytesIO(bytes(pdf.output()))
    buffer.seek(0)
    return buffer


class ToolifyPDF(FPDF):
    """PDF with a footer on every page."""

    def __init__(self, footer_text="Generated with Toolify"):
        super().__init__()
        self.footer_text = safe_text(footer_text)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, self.footer_text, align="C")


def parse_value(value):
    """Turn '25' into a number, but keep phone numbers / codes as text."""
    v = value.strip()
    if not v or len(v) > 12:
        return v
    if v.startswith("0") and not v.startswith("0."):
        return v
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


# -----------------------------
# HOME / DASHBOARD
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# Used by uptime pingers (UptimeRobot) to keep the free server awake
@app.route("/health")
def health():
    return "ok", 200


# -----------------------------
# RESUME BUILDER
# -----------------------------
@app.route("/resume", methods=["GET", "POST"])
def resume():
    if request.method == "POST":
        data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "location": request.form.get("location", "").strip(),
            "linkedin": request.form.get("linkedin", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "skills": request.form.get("skills", "").strip(),
            "education": request.form.get("education", "").strip(),
            "experience": request.form.get("experience", "").strip(),
            "projects": request.form.get("projects", "").strip(),
        }

        if not data["name"]:
            flash("Name is required.", "danger")
            return redirect(url_for("resume"))

        pdf = generate_resume_pdf(data)
        filename = f"{safe_filename(data['name'], 'My')}_Resume.pdf"
        return send_file(
            pdf_to_buffer(pdf),
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    return render_template("resume.html")


def generate_resume_pdf(data):
    data = {k: safe_text(v) for k, v in data.items()}

    pdf = ToolifyPDF("Generated with Toolify - Free online tools")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header - Name
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 12, data["name"], ln=True, align="C")

    # Contact info
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    contact_parts = [
        p for p in (data["email"], data["phone"], data["location"], data["linkedin"]) if p
    ]
    if contact_parts:
        pdf.multi_cell(0, 6, "  |  ".join(contact_parts), align="C")
    pdf.ln(4)

    # Horizontal line
    pdf.set_draw_color(30, 60, 120)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    def section_title(title):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 8, title.upper(), ln=True)
        pdf.set_draw_color(180, 180, 180)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    def body_text(text):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5.5, text)
        pdf.ln(3)

    sections = [
        ("Professional Summary", "summary"),
        ("Skills", "skills"),
        ("Work Experience", "experience"),
        ("Education", "education"),
        ("Projects", "projects"),
    ]
    for title, key in sections:
        if data[key]:
            section_title(title)
            body_text(data[key])

    return pdf


# -----------------------------
# PDF GENERATOR
# -----------------------------
@app.route("/pdf", methods=["GET", "POST"])
def pdf_generator():
    if request.method == "POST":
        title = request.form.get("title", "").strip() or "Document"
        content = request.form.get("content", "").strip()
        author = request.form.get("author", "").strip()

        if not content:
            flash("Content is required.", "danger")
            return redirect(url_for("pdf_generator"))

        pdf = ToolifyPDF(f"Generated with Toolify - {datetime.now().strftime('%d %b %Y')}")
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(20, 40, 80)
        pdf.multi_cell(0, 10, safe_text(title), align="C")
        pdf.ln(3)

        if author:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, safe_text(f"By {author}"), ln=True, align="C")
            pdf.ln(4)

        # Line
        pdf.set_draw_color(100, 100, 100)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        # Content
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6.5, safe_text(content))

        return send_file(
            pdf_to_buffer(pdf),
            as_attachment=True,
            download_name=f"{safe_filename(title, 'Document')}.pdf",
            mimetype="application/pdf",
        )

    return render_template("pdf_generator.html")


# -----------------------------
# EXCEL GENERATOR
# -----------------------------
@app.route("/excel", methods=["GET", "POST"])
def excel_generator():
    if request.method == "POST":
        title = request.form.get("title", "").strip() or "Sheet"
        headers_raw = request.form.get("headers", "").strip()
        data_raw = request.form.get("data", "").strip()

        if not headers_raw:
            flash("At least one header is required.", "danger")
            return redirect(url_for("excel_generator"))

        headers = [h.strip() for h in headers_raw.split(",") if h.strip()]
        rows = []
        if data_raw:
            for line in data_raw.splitlines():
                if line.strip():
                    cells = [c.strip() for c in line.split(",")]
                    # Pad or trim to match header length
                    while len(cells) < len(headers):
                        cells.append("")
                    rows.append(cells[: len(headers)])

        wb = Workbook()
        ws = wb.active
        ws.title = re.sub(r"[\\/*?:\[\]]", "", title)[:31] or "Sheet"  # Excel name rules

        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1E3C78", end_color="1E3C78", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC"),
        )

        # Write headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        # Write data (numbers become real numbers so sums/sorting work)
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=parse_value(value))
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cell.data_type = "s"  # keep as text, not a formula
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

        # Auto column width
        for col in ws.columns:
            max_length = max((len(str(c.value)) for c in col if c.value is not None), default=0)
            ws.column_dimensions[col[0].column_letter].width = min(max_length + 4, 40)

        # Freeze header
        ws.freeze_panes = "A2"

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{safe_filename(title, 'Sheet')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return render_template("excel_generator.html")


# -----------------------------
# IMAGE TO PDF
# -----------------------------
ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "bmp", "gif"}
MAX_IMAGES = 15


@app.route("/image-to-pdf", methods=["GET", "POST"])
def image_to_pdf():
    if request.method == "POST":
        files = [f for f in request.files.getlist("images") if f and f.filename]

        if not files:
            flash("Please choose at least one image.", "danger")
            return redirect(url_for("image_to_pdf"))
        if len(files) > MAX_IMAGES:
            flash(f"You can convert up to {MAX_IMAGES} images at a time.", "danger")
            return redirect(url_for("image_to_pdf"))

        pages = []
        for f in files:
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            if ext not in ALLOWED_IMAGE_EXT:
                flash(f"'{f.filename}' is not a supported image (use JPG, PNG or WEBP).", "danger")
                return redirect(url_for("image_to_pdf"))
            try:
                img = Image.open(f.stream)
                img.draft("RGB", (2000, 2000))  # saves memory for big JPEGs
                img = ImageOps.exif_transpose(img)  # fix sideways phone photos
                img.thumbnail((2000, 2000))
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGBA")
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")
                pages.append(img)
            except Exception:
                flash(f"Could not read '{f.filename}'. Try another image.", "danger")
                return redirect(url_for("image_to_pdf"))

        buffer = BytesIO()
        pages[0].save(
            buffer,
            "PDF",
            save_all=True,
            append_images=pages[1:],
            resolution=100.0,
        )
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="Toolify_Images.pdf",
            mimetype="application/pdf",
        )

    return render_template("image_to_pdf.html", max_images=MAX_IMAGES)


# -----------------------------
# ABOUT / FUTURE TOOLS
# -----------------------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(413)
def too_large(e):
    return "Files too large. Maximum total size is 25 MB.", 413


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
