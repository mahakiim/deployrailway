import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, request, current_app
from apscheduler.schedulers.background import BackgroundScheduler
import joblib
import numpy as np
from firebase_admin import db
from models.fb_init import init_firebase

# Setup logger
timestamp = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt=timestamp
)
logger = logging.getLogger(__name__)

# Initialize Firebase and load model
init_firebase()
base_dir = os.path.dirname(__file__)
model_path = os.path.join(base_dir, '..', 'models', 'gb_model2.pkl')
model = joblib.load(model_path)
logger.info(f"🧠 Model loaded from {model_path}")

# Blueprint for predict endpoints
predict_bp = Blueprint('predict', __name__)

FEATURE_KEYS = [
    'bojongsoang', 'dayeuhkolot',
    'Debit_Cipalasari', 'Debit_Citarum',
    'Debit_Hilir', 'TMA_hilir',
    'TMA_kolam', 'TMA_sungai'
]

def latest_value(node_dict):
    if not isinstance(node_dict, dict) or not node_dict:
        return 0
    return node_dict.get(sorted(node_dict)[-1], 0)

@predict_bp.route('/predict', methods=['GET', 'POST'])
def predict_endpoint():
    """
    POST: predict from JSON payload and upload.
    GET: read latest from Firebase, predict and upload.
    Returns JSON with pump_on and alert_level.
    """
    # Prepare input vector
    if request.method == 'POST':
        data = request.get_json() or {}
        vals = [data.get(k, 0) for k in FEATURE_KEYS]
    else:
        init_firebase()
        ref = db.reference('/Polder')
        vals = []
        for k in FEATURE_KEYS:
            node_data = ref.child(k).get() or {}
            v = latest_value(node_data)
            logger.info(f"Feature {k}: {v}")
            vals.append(v)

    arr = np.array(vals, float).reshape(1, -1)
    pump_pred, alert_pred = model.predict(arr)[0]
    logger.info(f"{request.method} /predict -> pump_on={pump_pred}, alert_level={alert_pred}")

    # Upload to Firebase
    init_firebase()
    ts = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d-%H_%M_%S')
    node = db.reference('/Polder')
    node.child('pump_on').child(ts).set(int(pump_pred))
    node.child('status_banjir').child(ts).set(int(alert_pred))

    return jsonify(pump_on=int(pump_pred), alert_level=int(alert_pred))

# Scheduled job runner
def run_predict_job():
    logger.info("[job] Running scheduled predict...")
    
    from app import app
    
    # test_client() akan otomatis handle context & request
    with app.test_client() as client:
        resp = client.get('/api/predict')
        try:
            data = resp.get_json()
            logger.info(f"[job] Scheduled predict response: {data}")
        except Exception as e:
            logger.error(f"[job] Failed to parse response: {e}")

# Scheduler setup
def schedule_predict(scheduler: BackgroundScheduler):
    scheduler.add_job(
        run_predict_job,           # sekarang jadwalkan run_predict_job
        trigger='interval',
        minutes=5,                 # atau minutes=5 di production
        id='predict_job',
        replace_existing=True,
        misfire_grace_time=120
    )
    logger.info("🗓️ Scheduled job 'predict_job' every 5 minutes")