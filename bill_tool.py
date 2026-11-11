"""Bill / invoice generator."""
from datetime import datetime

from flask import request
from fpdf import FPDF


def register(app, ctx):
    UserError = ctx.UserError
    send_pdf, make_view = ctx.send_pdf, ctx.make_view
    safe_text, safe_filename = ctx.safe_text, ctx.safe_filename

    # -----------------------------
    # BILL / INVOICE GENERATOR
    # -----------------------------
    def money(x):
        return f"{x:,.2f}"

    def do_bill():
        form = request.form
        seller = form.get("seller_name", "").strip()
        buyer = form.get("buyer_name", "").strip()
        if not seller or not buyer:
            raise UserError("Your shop name and the customer name are required.")

        rows = []
        for line in form.get("items", "").splitlines():
            if not line.strip():
                continue
            parts = line.rsplit(",", 2)
            if len(parts) != 3:
                raise UserError(f"Line '{line.strip()}' should look like: Item, quantity, rate")
            try:
                qty, rate = float(parts[1]), float(parts[2])
            except ValueError:
                raise UserError(f"Quantity and rate must be numbers in: {line.strip()}")
            if qty <= 0 or rate < 0:
                raise UserError(f"Quantity must be above 0 and rate cannot be negative in: {line.strip()}")
            rows.append((parts[0].strip(), qty, rate))
        if not rows:
            raise UserError("Please add at least one item.")
        if len(rows) > 50:
            raise UserError("You can add up to 50 items.")

        try:
            gst = float(form.get("gst_percent", "0") or 0)
        except ValueError:
            raise UserError("GST % must be a number.")
        if gst < 0 or gst > 100:
            raise UserError("GST % must be between 0 and 100.")

        subtotal = sum(q * r for _, q, r in rows)
        gst_amount = subtotal * gst / 100
        total = subtotal + gst_amount

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        def mc(width, height, text):
            pdf.multi_cell(width, height, text, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 10, "INVOICE", ln=True, align="R")

        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(30, 30, 30)
        mc(0, 7, safe_text(seller))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(80, 80, 80)
        if form.get("seller_address", "").strip():
            mc(0, 5, safe_text(form["seller_address"].strip()))
        if form.get("seller_gst", "").strip():
            pdf.cell(0, 5, safe_text("GSTIN: " + form["seller_gst"].strip()), ln=True)
        pdf.ln(4)

        pdf.set_draw_color(30, 60, 120)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(95, 6, "Bill to", ln=False)
        pdf.cell(0, 6, safe_text(f"Invoice no: {form.get('invoice_no', '').strip() or '-'}"), ln=True, align="R")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(95, 6, safe_text(buyer), ln=False)
        pdf.cell(0, 6, safe_text(f"Date: {form.get('date', '').strip() or datetime.now().strftime('%Y-%m-%d')}"),
                 ln=True, align="R")
        if form.get("buyer_address", "").strip():
            pdf.set_text_color(80, 80, 80)
            mc(95, 5, safe_text(form["buyer_address"].strip()))
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        with pdf.table(col_widths=(10, 85, 20, 35, 40),
                       text_align=("CENTER", "LEFT", "RIGHT", "RIGHT", "RIGHT")) as table:
            head = table.row()
            for h in ("No", "Item", "Qty", "Rate (Rs.)", "Amount (Rs.)"):
                head.cell(h)
            for i, (item, qty, rate) in enumerate(rows, 1):
                row = table.row()
                row.cell(str(i))
                row.cell(safe_text(item))
                row.cell(f"{qty:g}")
                row.cell(money(rate))
                row.cell(money(qty * rate))
        pdf.ln(4)

        def total_line(label, value, bold=False):
            pdf.set_font("Helvetica", "B" if bold else "", 11 if bold else 10)
            pdf.cell(135, 7, label, align="R")
            pdf.cell(55, 7, "Rs. " + money(value), ln=True, align="R")

        total_line("Subtotal:", subtotal)
        if gst:
            total_line(f"GST ({gst:g}%):", gst_amount)
        total_line("Total:", total, bold=True)

        if form.get("notes", "").strip():
            pdf.ln(6)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(90, 90, 90)
            mc(0, 5, safe_text(form["notes"].strip()))

        pdf.set_y(-15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Generated with Toolify", align="C")

        return send_pdf(bytes(pdf.output()), f"Invoice_{safe_filename(form.get('invoice_no', ''), 'bill')}.pdf")


    app.add_url_rule("/bill-generator", "bill_generator", make_view("bill_generator", do_bill),
                     methods=["GET", "POST"])
