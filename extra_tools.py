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