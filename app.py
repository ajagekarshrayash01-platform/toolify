from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "toolify-secret-key-change-in-production")

# -----------------------------
# HOME / DASHBOARD
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


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
        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)

        filename = f"{data['name'].replace(' ', '_')}_Resume.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    return render_template("resume.html")


def generate_resume_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header - Name
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(30, 60, 120)
    pdf.cell(0, 12, data["name"], ln=True, align="C")

    # Contact info
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    contact_parts = []
    if data["email"]:
        contact_parts.append(data["email"])
    if data["phone"]:
        contact_parts.append(data["phone"])
    if data["location"]:
        contact_parts.append(data["location"])
    if data["linkedin"]:
        contact_parts.append(data["linkedin"])
    contact_line = "  |  ".join(contact_parts)
    pdf.cell(0, 8, contact_line, ln=True, align="C")
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

    # Summary
    if data["summary"]:
        section_title("Professional Summary")
        body_text(data["summary"])

    # Skills
    if data["skills"]:
        section_title("Skills")
        body_text(data["skills"])

    # Experience
    if data["experience"]:
        section_title("Work Experience")
        body_text(data["experience"])

    # Education
    if data["education"]:
        section_title("Education")
        body_text(data["education"])

    # Projects
    if data["projects"]:
        section_title("Projects")
        body_text(data["projects"])

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Generated with Toolify • Free online tools", align="C")

    return pdf


# -----------------------------
# PDF GENERATOR
# -----------------------------
@app.route("/pdf", methods=["GET", "POST"])
def pdf_generator():
    if request.method == "POST":
        title = request.form.get("title", "Document").strip()
        content = request.form.get("content", "").strip()
        author = request.form.get("author", "").strip()

        if not content:
            flash("Content is required.", "danger")
            return redirect(url_for("pdf_generator"))

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(20, 40, 80)
        pdf.cell(0, 12, title, ln=True, align="C")
        pdf.ln(3)

        if author:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 8, f"By {author}", ln=True, align="C")
            pdf.ln(4)

        # Line
        pdf.set_draw_color(100, 100, 100)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        # Content
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6.5, content)

        # Footer
        pdf.set_y(-15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, f"Generated with Toolify • {datetime.now().strftime('%Y-%m-%d')}", align="C")

        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)

        filename = f"{title.replace(' ', '_')[:40]}.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    return render_template("pdf_generator.html")


# -----------------------------
# EXCEL GENERATOR
# -----------------------------
@app.route("/excel", methods=["GET", "POST"])
def excel_generator():
    if request.method == "POST":
        title = request.form.get("title", "Sheet").strip() or "Sheet"
        headers_raw = request.form.get("headers", "").strip()
        data_raw = request.form.get("data", "").strip()

        if not headers_raw:
            flash("At least one header is required.", "danger")
            return redirect(url_for("excel_generator"))

        headers = [h.strip() for h in headers_raw.split(",") if h.strip()]
        rows = []
        if data_raw:
            for line in data_raw.strip().split("\n"):
                if line.strip():
                    cells = [c.strip() for c in line.split(",")]
                    # Pad or trim to match header length
                    while len(cells) < len(headers):
                        cells.append("")
                    rows.append(cells[:len(headers)])

        wb = Workbook()
        ws = wb.active
        ws.title = title[:31]  # Excel sheet name limit

        # Styles
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="1E3C78", end_color="1E3C78", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC")
        )

        # Write headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        # Write data
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

        # Auto column width
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            ws.column_dimensions[column].width = min(max_length + 4, 40)

        # Freeze header
        ws.freeze_panes = "A2"

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"{title.replace(' ', '_')[:40]}.xlsx"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    return render_template("excel_generator.html")


# -----------------------------
# ABOUT / FUTURE TOOLS
# -----------------------------
@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
