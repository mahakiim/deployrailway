# controllers/predict.py

import os
import re
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import joblib
import numpy as np
from firebase_admin import db
from models.fb_init import init_firebase

# — Setup logger sesuai PUEBI —
timestamp = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt=timestamp
)
logger = logging.getLogger(__name__)

# — Inisialisasi Firebase & load model Decision Tree terbaru —
init_firebase()
base_dir   = os.path.dirname(__file__)
model_path = os.path.join(base_dir, '..', 'models', 'dt_model_fix.pkl')
model      = joblib.load(model_path)
logger.info(f"🧠 Decision Tree model loaded from {model_path}")

# — Blueprint untuk endpoint /predict —
predict_bp = Blueprint('predict', __name__)

# — Daftar fitur sesuai data pelatihan model —
FEATURE_KEYS = [
    'Debit_Cipalasari',
    'Debit_Hilir',
    'Debit_Hulu',
    'TMA_Cipalasari',
    'TMA_Citarum',
    'TMA_Kolam'
]

def latest_value(node_dict: dict) -> float:
    """Ambil nilai terbaru dari node Firebase (berdasarkan key terakhir)."""
    if not isinstance(node_dict, dict) or not node_dict:
        return 0.0
    return node_dict.get(sorted(node_dict)[-1], 0.0)

@predict_bp.route('/predict', methods=['GET', 'POST'])
def predict_endpoint():


    """
    Prediksi status banjir & rekomendasi pompa
    ---
    tags:
      - Prediksi
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            Debit_Cipalasari:
              type: number
            Debit_Hilir:
              type: number
            Debit_Hulu:
              type: number
            TMA_Cipalasari:
              type: number
            TMA_Citarum:
              type: number
            TMA_Kolam:
              type: number
    responses:
      200:
        description: Hasil prediksi
        schema:
          type: object
          properties:
            pump_on:
              type: integer
              description: Status pompa (0–3)
            alert_level:
              type: integer
              description: Level siaga banjir (0–3)
      400:
        description: Invalid JSON payload
    """

    # — Siapkan vektor input —
    if request.method == 'POST':
        raw   = request.get_data(as_text=True)
        clean = re.sub(r'[\x00-\x1f]+', '', raw)          # buang control chars
        try:
            payload = json.loads(clean, strict=False)
        except json.JSONDecodeError as e:
            logger.error(f"Gagal decode JSON: {e}")
            return jsonify(error="Invalid JSON payload"), 400

        vals = [ float(payload.get(k, 0)) for k in FEATURE_KEYS ]

    else:
        ref  = db.reference('/Polder')
        vals = []
        for k in FEATURE_KEYS:
            node_data = ref.child(k).get() or {}
            v         = latest_value(node_data)
            logger.info(f"Feature {k}: {v}")
            vals.append(float(v))

    # — Prediksi status banjir saja —
    arr       = np.array(vals, dtype=float).reshape(1, -1)
    alert_pred = int(model.predict(arr)[0])
    logger.info(f"{request.method} /predict -> alert_level={alert_pred}")

    # — Rekomendasi pompa berdasarkan TMA_Kolam (cm) —
    tma_kolam     = vals[FEATURE_KEYS.index('TMA_Kolam')]
    if   tma_kolam <  3.2: pump_pred = 0
    elif tma_kolam <= 9.6: pump_pred = 1
    elif tma_kolam <=14.0: pump_pred = 2
    else:                  pump_pred = 3

    logger.info(f"Rekomendasi pompa (berdasarkan TMA_Kolam): {pump_pred}")

    # — Upload hasil ke Firebase —
    ts   = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d-%H_%M_%S')
    node = db.reference('/Polder')
    node.child('pump_on').child(ts).set(pump_pred)
    node.child('status_banjir').child(ts).set(alert_pred)

    # — Kirim respon ke klien —
    return jsonify(pump_on=pump_pred, alert_level=alert_pred), 200


# — Scheduled job runner (opsional) —
def run_predict_job():
    logger.info("[job] Running scheduled predict…")
    from app import app
    with app.test_client() as client:
        resp = client.get('/api/predict')
        try:
            data = resp.get_json()
            logger.info(f"[job] Scheduled predict response: {data}")
        except Exception as e:
            logger.error(f"[job] Failed to parse response: {e}")

def schedule_predict(scheduler: BackgroundScheduler):
    scheduler.add_job(
        run_predict_job,
        trigger='interval',
        minutes=1,
        id='predict_job',
        replace_existing=True,
        misfire_grace_time=120
    )
    logger.info("🗓️ Scheduled job 'predict_job' every 1 minute")
