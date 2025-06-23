import os, re
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from models.bmkg_api import fetch_all_locations

load_dotenv(override=True)

def init_firebase():
    if not firebase_admin._apps:
        raw = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
        # ===== Tambahkan debug di sini =====
        print("DEBUG raw env:", repr(raw))
        # ===================================
        # strip quotes & normalize newline
        raw = raw.strip()
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            raw = raw[1:-1]
        raw = raw.replace("\r\n", "\\n").replace("\n", "\\n").replace("\\\\n", "\\n")

        cred_dict = json.loads(raw)
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(
            cred,
            {"databaseURL": os.getenv("DATABASE_URL")}
        )
        print("✅ Firebase initialized successfully")
    else:
        print("⚠️ Firebase already initialized, skipping...")

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