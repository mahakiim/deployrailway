import os
from flask import Blueprint, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

from models.fb_init import upload_to_firebase
from models.bmkg_api import fetch_all_locations

weather_bp = Blueprint("weather", __name__)

@weather_bp.route('/trigger', methods=['POST'])
def manual_trigger():
    print("[weather] Trigger endpoint called")
    try:
        print("[weather] Starting upload to Firebase...")
        upload_to_firebase()
        print("[weather] Upload successful")
        return jsonify(status='success', message='Data cuaca berhasil diupload ke Firebase'), 200
    except Exception as e:
        print(f"[weather] Upload failed: {e}")
        return jsonify(status='error', message=f'Gagal upload: {e}'), 500
    
@weather_bp.route('/curah-hujan', methods=['GET'])
def get_curah_hujan():
    print("[weather] GET /curah-hujan called")
    data = fetch_all_locations()
    print(f"[weather] Fetched locations: {list(data.keys())}")
    return jsonify(data)

def schedule_job(scheduler: BackgroundScheduler):
    print("[weather] Scheduling upload job every 5 minutes")
    scheduler.add_job(
        upload_to_firebase,
        trigger='interval',
        seconds=5,
        id='weather_upload_job',
        replace_existing=True
    )
    print("[weather] Scheduled job 'weather_upload_job'")
