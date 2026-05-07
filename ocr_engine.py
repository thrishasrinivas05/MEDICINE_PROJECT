import easyocr
import cv2
import re

from difflib import get_close_matches

# EASY OCR READER
reader = easyocr.Reader(['en'])


# ================= TEXT EXTRACTION =================
def extract_text(image_path):

    img = cv2.imread(image_path)

    img = cv2.resize(img, None, fx=2, fy=2)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    results = reader.readtext(gray, detail=0)

    text = " ".join(results)

    print("OCR RESULT:", text)

    return text


# ================= MEDICINE NAME =================
def extract_medicine_name(text):

    print("RAW OCR:", text)

    medicine_database = [

        "Cetirizine",
        "Paracetamol",
        "Azithromycin",
        "Amoxicillin",
        "Ibuprofen",
        "Dolo",
        "Crocin",
        "Aspirin",
        "Metformin",
        "Pantoprazole",
        "Omeprazole",
        "Zincovit",
        "Montek",
        "Sinarest",
        "Calpol",
        "Benadryl",
        "Augmentin",
        "Azee",
        "Telma",
        "Shelcal"
    ]

    words = re.findall(r'[A-Za-z]+', text)

    print("OCR WORDS:", words)

    best_match = None

    for word in words:

        if len(word) < 4:
            continue

        matches = get_close_matches(
            word.capitalize(),
            medicine_database,
            n=1,
            cutoff=0.6
        )

        if matches:
            best_match = matches[0]
            break

    if best_match:
        return best_match

    return "Unknown Medicine"


# ================= EXPIRY =================
def extract_expiry(text):

    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)

    if match:
        return match.group()

    return None