from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import re

from db import insert_user, get_user
from db import insert_medicine, get_all_medicines, delete_medicine

import cv2
import pytesseract

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "medicine_project_key")

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "images")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ⚠️ DO NOT set tesseract path on Render
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ================= LOGIN =================
@app.route('/')
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_check():
    email = request.form.get("email")
    password = request.form.get("password")

    user = get_user(email)

    if user and user.get("password") == password:
        session["user"] = email
        return redirect(url_for("upload_page"))

    return render_template("login.html", error="Invalid credentials")


# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")

    if get_user(email):
        return render_template("login.html", error="User already exists")

    insert_user({
        "name": name,
        "email": email,
        "phone": phone,
        "password": password
    })

    return render_template("login.html", success="Registered successfully")


# ================= UPLOAD PAGE =================
@app.route('/upload_page')
def upload_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


# ================= TEXT CLEAN =================
def clean_ocr_text(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ================= NAME EXTRACTION =================
def extract_medicine_name(text):
    text = clean_ocr_text(text)
    words = text.split()

    ignore = {"TABLET","CAPSULE","CAP","TAB","MG","ML","IP","BP","USP"}

    name_parts = []

    for w in words:
        if w in ignore or len(w) <= 2 or w.isdigit():
            continue
        name_parts.append(w)
        if len(name_parts) >= 3:
            break

    return " ".join(name_parts).title() if name_parts else "Unknown"


# ================= EXPIRY =================
def normalize_expiry(text):
    text = clean_ocr_text(text)

    months = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04",
        "MAY":"05","JUN":"06","JUL":"07","AUG":"08",
        "SEP":"09","OCT":"10","NOV":"11","DEC":"12"
    }

    match = re.search(r'([A-Z]{3})\s*([0-9]{4})', text)
    if match:
        m, y = match.groups()
        return f"{y}-{months.get(m,'01')}-01"

    return None


# ================= UPLOAD =================
@app.route('/upload', methods=['POST'])
def upload():

    if "user" not in session:
        return redirect(url_for("login"))

    file = request.files.get('file')

    if not file or file.filename == '':
        return "No file selected"

    filename = file.filename.replace(" ", "_")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # ⚡ SAFE IMAGE READ
    img = cv2.imread(filepath)

    if img is None:
        return "Invalid image file"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=0.5, fy=0.5)

    # ⚠ OCR (slow part)
    text = pytesseract.image_to_string(gray, config='--psm 6')

    medicine_name = extract_medicine_name(text)
    expiry_date = normalize_expiry(text)

    manual_name = request.form.get("manual_name")
    manual_expiry = request.form.get("manual_expiry")

    if manual_name:
        medicine_name = manual_name.strip()

    if manual_expiry:
        expiry_date = manual_expiry

    stock = request.form.get("stock")
    stock = int(stock) if stock and stock.isdigit() else 0

    insert_medicine({
        "medicine_name": medicine_name,
        "stock": stock,
        "expiry_date": expiry_date,
        "order_date": datetime.now().strftime("%Y-%m-%d"),
        "image": filename
    })

    return redirect(url_for("dashboard"))


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    medicines = get_all_medicines()
    today = datetime.now().date()

    for med in medicines:
        try:
            if med.get("expiry_date"):
                exp = datetime.strptime(med["expiry_date"], "%Y-%m-%d").date()
                med["days_left"] = (exp - today).days
        except:
            med["days_left"] = None

    return render_template("dashboard.html", medicines=medicines)


# ================= DELETE =================
@app.route('/delete/<id>')
def delete(id):
    delete_medicine(id)
    return redirect(url_for("dashboard"))


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))