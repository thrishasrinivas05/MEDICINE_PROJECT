import os
from pymongo import MongoClient
from bson.objectid import ObjectId

MONGO_URI = os.environ.get("mongodb+srv://<thrishasrinivas05_db_user>:<x3MpVqAKhRtLPG0G>@cluster0.nct3v0b.mongodb.net/?appName=Cluster0")

if not MONGO_URI:
    raise Exception("MONGO_URI NOT FOUND in Render environment variables")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["medicineDB"]

medicine_collection = db["medicines"]
user_collection = db["users"]


# ================= MEDICINES =================
def insert_medicine(data):
    medicine_collection.insert_one(data)


def get_all_medicines():
    return list(medicine_collection.find())


def delete_medicine(id):
    medicine_collection.delete_one({"_id": ObjectId(id)})


# ================= USERS =================
def insert_user(data):
    user_collection.insert_one(data)


def get_user(email):
    return user_collection.find_one({"email": email})