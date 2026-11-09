# Toolify — Free Online Document Tools

A simple, clean Flask web app with:

- **Resume Builder** → Professional PDF resume
- **PDF Generator** → Text to PDF
- **Excel Generator** → Create styled .xlsx files

No signup required. Perfect starting point for a free tools website you can monetize later.

---

## Local Development

```bash
# 1. Go to project folder
cd toolify

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open: http://127.0.0.1:5000

---

## Deploy to Render (Free)

1. Push this project to a **GitHub** repository.
2. Go to [https://render.com](https://render.com) → Sign up / Log in.
3. Click **New +** → **Web Service**.
4. Connect your GitHub repo.
5. Settings:
   - **Name**: `toolify` (or any name)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free
6. Click **Create Web Service**.

Render will give you a free URL like `https://toolify-xxxx.onrender.com`.

> Note: Free tier on Render sleeps after 15 min of inactivity. First load after sleep may take 30–50 seconds.

### Optional Environment Variable
- `SECRET_KEY` → set any random string for production security.

---

## Other Free Hosting Options

| Platform     | Notes                              |
|--------------|------------------------------------|
| **Render**   | Best free tier for Flask           |
| **Railway**  | Easy, good free credits            |
| **PythonAnywhere** | Simple, free limited plan     |
| **Fly.io**   | Slightly more setup                |

---

## Project Structure

```
toolify/
├── app.py                 # Main Flask application
├── requirements.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── resume.html
│   ├── pdf_generator.html
│   ├── excel_generator.html
│   └── about.html
└── static/                # (empty for now, ready for custom CSS/JS)
```

---

## Monetization Ideas (Later)

1. **Google AdSense** — Add ads in the footer / sidebar after you get traffic.
2. **Freemium** — Free version has a small footer watermark. Paid version removes it + extra templates.
3. **Premium Resume Templates** — Charge ₹49–149 for nicer designs.
4. **Affiliate links** — Promote Canva, Notion, hosting, etc.

---

## Next Tools You Can Add

- Invoice / Bill Generator
- Gas / Utility bill style PDF
- Image → PDF
- PDF → Text / basic converter
- More resume templates

The code is structured so adding new routes and templates is straightforward.

---

Made with ❤️ for productivity.
