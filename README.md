# Toolify

**All-in-one free online tools** for PDFs, images and documents. No signup. Your files are processed in memory and are not stored.

🔗 **Live site:** https://toolify-c6ns.onrender.com

> Note: the site runs on a free server, so the first visit after a quiet period can take 30-60 seconds to load.

---

## Tools

### PDF Tools
| Tool | What it does |
|---|---|
| Image to PDF | Combine JPG, PNG or WEBP images into one PDF |
| PDF to JPG | Convert every PDF page to a JPG (ZIP for many pages) |
| Merge PDF | Join several PDFs into one |
| Split PDF | Extract pages, or split every page into its own file |
| Compress PDF | Reduce PDF file size |
| Lock PDF | Add a password (AES-256) |
| Unlock PDF | Remove a password when you know it |
| PDF Generator | Turn text into a neat PDF |

### Image Tools
| Tool | What it does |
|---|---|
| Image Converter | Convert between JPG, PNG and WEBP |
| Resize & Compress Image | Resize, or compress to a target size in KB (useful for exam and job forms) |

### Document Tools
| Tool | What it does |
|---|---|
| Resume Builder | Fill a form and download a clean PDF resume |
| Bill / Invoice Generator | Create an invoice PDF with items and GST |
| Excel Generator | Create `.xlsx` sheets with headers and data |

---

## Tech stack

- **Backend:** Python, Flask
- **PDF:** PyMuPDF, fpdf2
- **Images:** Pillow
- **Excel:** openpyxl
- **Frontend:** Jinja2 templates, Bootstrap 5, Bootstrap Icons
- **Server:** Gunicorn on Render (free plan)

---

## Project structure

```
toolify/
├── app.py               # Flask app, tool list, resume/PDF/Excel/image-to-PDF routes, SEO routes
├── extra_tools.py       # Shared helpers, loads the tool modules below
├── tool_pages.py        # Text and form fields for each tool page
├── pdf_tools.py         # Merge, split, compress, lock, unlock, PDF to JPG
├── image_tools.py       # Image converter, resize and compress
├── bill_tool.py         # Bill / invoice generator
├── gunicorn.conf.py     # Gunicorn settings (threads, timeout)
├── requirements.txt
├── Procfile
└── templates/
    ├── base.html        # Layout, navbar, footer
    ├── index.html       # Homepage
    ├── tool_page.html   # Shared template for most tools
    ├── image_to_pdf.html
    ├── resume.html
    ├── pdf_generator.html
    ├── excel_generator.html
    └── about.html
```

---

## Run locally

```bash
git clone https://github.com/<your-username>/toolify.git
cd toolify
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

---

## Deploy on Render

1. Push this repo to GitHub.
2. On Render, create a **Web Service** and connect the repo.
3. Use these settings:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
   - **Instance type:** Free
4. Optional: set a `SECRET_KEY` environment variable.
5. Optional: add a free uptime monitor (for example UptimeRobot) on `/health` to keep the site awake.

---

## Add a new tool

1. Add its page text and form fields to `tool_pages.py`.
2. Write its handler and route in a tool module (see `pdf_tools.py` for an example).
3. Add one entry to `TOOL_GROUPS` in `app.py`. The menu, homepage cards, footer and sitemap update automatically.

---

## Roadmap

- [ ] PDF to Word
- [ ] QR Code Generator
- [ ] PDF Watermark, Rotate and Page Numbers
- [ ] Support (QR) button, Privacy Policy and Contact pages
- [ ] User accounts and saved records

---

## Privacy

Uploaded files are processed in memory and sent back to you. They are not saved on the server.

---

## License

PDF features use [PyMuPDF](https://pymupdf.readthedocs.io/), which is licensed under AGPL-3.0. Check its license terms before using or redistributing this project commercially.
