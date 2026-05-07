from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os

from db import (
    insert_user,
    get_user,
    insert_medicine,
    get_all_medicines,
    delete_medicine
)

# ================= OCR IMPORT =================
try:
    from ocr_engine import (
        extract_text,
        extract_medicine_name,
        extract_expiry
    )
except:
    extract_text = lambda x: ""
    extract_medicine_name = lambda x: "Unknown Medicine"
    extract_expiry = lambda x: "Not Found"

# ================= ML IMPORT =================
try:
    from ml_model import predict_stock_status, expiry_alert
except:
    predict_stock_status = lambda x: "OK"
    expiry_alert = lambda x: "UNKNOWN"

# ================= APP =================
app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = os.getenv(
    "SECRET_KEY",
    "medicine_project_key"
)

# ================= SESSION FIX =================
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False

# ================= UPLOAD FOLDER =================
UPLOAD_FOLDER = "/tmp"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= LOGIN PAGE =================
@app.route('/')
def login():
    return render_template("login.html")


# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login_check():

    email = request.form.get("email")
    password = request.form.get("password")

    user = get_user(email)

    if user and user.get("password") == password:
        session["user"] = email
        return redirect(url_for("upload_page"))

    return render_template(
        "login.html",
        error="Invalid login"
    )


# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():

    email = request.form.get("email")

    if get_user(email):
        return render_template(
            "login.html",
            error="User already exists"
        )

    insert_user({
        "name": request.form.get("name"),
        "email": email,
        "phone": request.form.get("phone"),
        "password": request.form.get("password")
    })

    return render_template(
    "login.html",
    success="Registration Successful! Please Login."
)


# ================= UPLOAD PAGE =================
@app.route('/upload_page')
def upload_page():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")


# ================= UPLOAD =================
@app.route('/upload', methods=['POST'])
def upload():

    try:

        if "user" not in session:
            return redirect(url_for("login"))

        # ===== FILE CHECK =====
        if "file" not in request.files:
            return "No file uploaded"

        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        # ===== SAVE FILE =====
        filename = file.filename.replace(" ", "_")

        filepath = os.path.join(
            UPLOAD_FOLDER,
            filename
        )

        file.save(filepath)

        # ===== OCR =====
        try:

            text = extract_text(filepath)

            print("OCR TEXT:", text)

            ocr_name = extract_medicine_name(text)

            ocr_expiry = None

        except Exception as e:

            print("OCR ERROR:", e)

            ocr_name = "Unknown Medicine"

            ocr_expiry = "Not Found"

        # ===== FORM INPUT =====
        name = request.form.get(
            "manual_name"
        ) or ocr_name

        expiry = request.form.get(
            "manual_expiry"
        ) or ocr_expiry

        stock = int(
            request.form.get("stock") or 0
        )

        # ===== ML =====
        try:

            stock_status = predict_stock_status(stock)

            expiry_status = (
                expiry_alert(expiry)
                if expiry else "UNKNOWN"
            )

        except Exception as e:

            print("ML ERROR:", e)

            stock_status = "OK"

            expiry_status = "UNKNOWN"

        # ===== SAVE DATABASE =====
        insert_medicine({

            "medicine_name": name,

            "stock": stock,

            "expiry_date": expiry,

            "order_date": datetime.now().strftime(
                "%d-%m-%Y"
            ),

            "image": filename,

            "stock_status": stock_status,

            "expiry_status": expiry_status
        })

        return redirect(url_for("dashboard"))

    except Exception as e:

        print("UPLOAD ERROR:", e)

        return "Upload Failed"

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    medicines = get_all_medicines()

    low_stock = []

    expiring = []

    today = datetime.now().date()

    for m in medicines:

        # ===== LOW STOCK =====
        if m.get("stock", 0) <= 5:

            low_stock.append(
                m.get("medicine_name")
            )

        # ===== EXPIRY CHECK =====
        try:

            if m.get("expiry_date"):

                # DATE FROM CALENDAR INPUT
                exp = datetime.strptime(
                    m["expiry_date"],
                    "%Y-%m-%d"
                ).date()

                days = (exp - today).days

                # POPUP ALERT
                if 0 <= days <= 30:

                    expiring.append(
                        f"{m['medicine_name']} expires in {days} days"
                    )

                # SHOW FORMAT
                m["expiry_date"] = exp.strftime(
                    "%d-%m-%Y"
                )

        except Exception as e:

            print("DATE ERROR:", e)

    return render_template(

        "dashboard.html",

        medicines=medicines,

        popup_msg=(
            "\n".join(expiring)
            if expiring else None
        ),

        low_stock_msg=(
            ", ".join(low_stock)
            if low_stock else None
        )
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
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000,
        debug=True
    )