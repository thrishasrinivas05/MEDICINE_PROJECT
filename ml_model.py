from datetime import datetime

# =========================
# AI STOCK PREDICTION
# =========================
def predict_stock_status(stock, daily_usage=5):

    if stock <= 0:
        return "OUT OF STOCK "

    days_left = stock / daily_usage

    if stock <= 10:
        return "CRITICAL STOCK  - REORDER NOW"

    elif days_left <= 5:
        return "LOW STOCK  - ORDER SOON"

    else:
        return "STOCK OK "


# =========================
# EXPIRY ALERT SYSTEM (FINAL FIXED)
# =========================
def expiry_alert(expiry_date_str):

    try:
        expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
    except:
        return "EXPIRY FORMAT ERROR"

    today = datetime.today()
    days_left = (expiry_date - today).days

    if days_left < 0:
        return "EXPIRED  DO NOT USE"

    elif days_left <= 30:
        return f"EXPIRING SOON  ({days_left} days left)"

    elif days_left <= 90:
        return f"NEAR EXPIRY ({days_left} days left)"

    else:
        return f"SAFE ✔ ({days_left} days left)"