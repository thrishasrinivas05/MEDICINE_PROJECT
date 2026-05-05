from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient("mongodb://localhost:27017/")
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