from bson.objectid import ObjectId

users = []
medicines = []

def insert_user(data):
    users.append(data)

def get_user(email):
    for u in users:
        if u["email"] == email:
            return u
    return None

def insert_medicine(data):
    data["_id"] = str(ObjectId())
    medicines.append(data)

def get_all_medicines():
    return medicines

def delete_medicine(mid):
    global medicines
    medicines = [m for m in medicines if m["_id"] != mid]