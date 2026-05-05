from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os
import re
import time
from db import insert_user, get_user
from db import insert_medicine, get_all_medicines, delete_medicine

import cv2
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = "medicine_project_key"

UPLOAD_FOLDER = "static/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= LOGIN =================
@app.route('/')
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_check():
    email = request.form["email"]
    password = request.form["password"]

    user = get_user(email)

    if user:
        if user["password"] == password:
            session["user"] = email
            return redirect(url_for("upload_page"))
        else:
            return render_template("login.html", error="Invalid Password")
    else:
        return render_template("login.html", error="User not found")
    
# ==================REGISTER ===================
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")

    # check if user already exists
    if get_user(email):
        return render_template("login.html", error="User already exists")

    # save to MongoDB
    insert_user({
        "name": name,
        "email": email,
        "phone": phone,
        "password": password
    })

    return render_template("login.html", success="Registered successfully! Please login")


# ================= UPLOAD PAGE =================
@app.route('/upload_page')
def upload_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


# ================= OCR CLEAN =================
def clean_ocr_text(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ================= NAME =================
def extract_medicine_name(text):
    text = clean_ocr_text(text)
    text = re.split(r'EXP|MFG|MFD|BATCH', text)[0]

    words = text.split()

    ignore = {
        "TABLET","CAPSULE","CAP","TAB",
        "MG","ML","IP","BP","USP",
        "COMPOSITION","COATED","FILM"
    }

    name_parts = []

    for w in words:
        if w in ignore:
            continue
        if len(w) <= 2:
            continue
        if re.match(r'^\d+$', w):
            continue

        name_parts.append(w)

        if len(name_parts) >= 3:
            break

    name = " ".join(name_parts)

    return name.title() if name else "Unknown Medicine"


# ================= EXPIRY =================
def normalize_expiry(text):
    text = clean_ocr_text(text)

    months = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04",
        "MAY":"05","JUN":"06","JUL":"07","AUG":"08",
        "SEP":"09","OCT":"10","NOV":"11","DEC":"12"
    }

    match = re.search(r'EXP\s*([A-Z]{3})\s*([0-9]{4})', text)
    if match:
        m, y = match.groups()
        return f"{y}-{months.get(m,'01')}-01"

    match = re.search(r'([A-Z]{3})\s*([0-9]{4})', text)
    if match:
        m, y = match.groups()
        if m in months:
            return f"{y}-{months[m]}-01"

    match = re.search(r'([0-9]{2})[/\-]([0-9]{4})', text)
    if match:
        m, y = match.groups()
        return f"{y}-{m}-01"

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

    img = cv2.imread(filepath)
    img = cv2.resize(img, None, fx=0.6, fy=0.6)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    text = pytesseract.image_to_string(thresh, config='--psm 6')

    ocr_name = extract_medicine_name(text)
    ocr_expiry = normalize_expiry(text)

    manual_name = request.form.get("manual_name")
    manual_expiry = request.form.get("manual_expiry")

    medicine_name = manual_name.strip() if manual_name else ocr_name

    if not medicine_name or medicine_name == "Unknown Medicine":
        medicine_name = text[:25].strip()

    expiry_date = manual_expiry if manual_expiry else ocr_expiry

    stock = request.form.get("stock")
    stock = int(stock) if stock and stock.isdigit() else 0

    data = {
        "medicine_name": medicine_name,
        "stock": stock,
        "expiry_date": expiry_date,
        "order_date": datetime.now().strftime("%Y-%m-%d"),
        "image": filename
    }

    insert_medicine(data)

    return redirect(url_for("dashboard"))

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    medicines = get_all_medicines()

    low_items = []
    expiring_list = []

    today = datetime.now().date()

    for med in medicines:

        # ===== LOW STOCK =====
        if med.get("stock", 0) <= 5:
            low_items.append(med.get("medicine_name", "Unknown"))

        # ===== EXPIRY =====
        try:
            if med.get("expiry_date"):
                exp_date = datetime.strptime(med["expiry_date"], "%Y-%m-%d").date()
                days_left = (exp_date - today).days

                med["days_left"] = days_left
                med["is_expiring"] = 0 <= days_left <= 30

                if med["is_expiring"]:
                    expiring_list.append(
                        f"{med.get('medicine_name')} → {days_left} days ({exp_date.strftime('%d-%m-%Y')})"
                    )
            else:
                med["is_expiring"] = False

        except:
            med["is_expiring"] = False

        # ===== FORMAT DATE =====
        try:
            med["expiry_date"] = datetime.strptime(
                med["expiry_date"], "%Y-%m-%d"
            ).strftime("%d-%m-%Y")
        except:
            pass

    #  RIGHT SIDE ALERT (ONLY EXPIRY)
    popup_msg = None
    if expiring_list:
        popup_msg = "\n".join(expiring_list)

    #  BOTTOM BAR (ONLY LOW STOCK)
    low_stock_msg = None
    if low_items:
        low_stock_msg = ", ".join(low_items)

    return render_template(
        "dashboard.html",
        medicines=medicines,
        popup_msg=popup_msg,
        low_stock_msg=low_stock_msg
    )


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
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))