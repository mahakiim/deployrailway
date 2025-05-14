import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from models.bmkg_api import fetch_all_locations

load_dotenv()

def init_firebase():
    if not firebase_admin._apps:
        cred = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON", "{}"))
        firebase_admin.initialize_app(
            credentials.Certificate(cred),
            {"databaseURL": os.getenv("DATABASE_URL")}
        )

def upload_to_firebase():
    init_firebase()
    root_ref = db.reference("/Polder")
    data_dict = fetch_all_locations()

    for lokasi, data in data_dict.items():
        node = root_ref.child(lokasi)
        
        if "error" in data :
            node.set(data)

        else:
            node.update(data)

    print("✅ Data cuaca berhasil diupload ke Firebase")