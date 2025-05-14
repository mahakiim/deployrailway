# model/bmkg_api.py

import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# Mapping kode wilayah ke nama lokasi
ADM_CODES = {
    "32.04.12.2002": "bojongsoang",
    "32.04.12.2003": "dayeuhkolot"
}

def get_next_weather(adm_code: str) -> dict | None:
    """
    Fetch prakiraan cuaca terbaru untuk adm_code tertentu.
    Return: { ISO_TIME: tp } atau None kalau gagal.
    """
    url = f'https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={adm_code}'
    res = requests.get(url)
    if res.status_code != 200:
        return None

    payload = res.json().get("data", [])
    if not payload:
        return None

    # Loop untuk ambil entri cuaca pertama yg waktu-nya setelah sekarang
    cuaca_list = payload[0].get("cuaca", [])
    for cuaca in cuaca_list:
        for item in cuaca:
            # parsing UTC → WIB
            waktu_utc = datetime.strptime(item["datetime"], "%Y-%m-%dT%H:%M:%SZ") \
                              .replace(tzinfo=ZoneInfo("UTC"))
            waktu_wib = waktu_utc.astimezone(ZoneInfo("Asia/Jakarta"))
            if waktu_wib > datetime.now(ZoneInfo("Asia/Jakarta")):
                key = waktu_wib.strftime("%Y-%m-%d-%H_%M_%S")
                return { key: item["tp"] }

    return None

def fetch_all_locations() :
    """
    Loop semua kode ADM_CODES, return dict:
    {
      "bojongsoang": { ISO_TIME: tp } atau {"error": "..."},
      "dayeuhkolot": { ... }
    }
    """
    hasil = {}
    for code, nama in ADM_CODES.items():
        data = get_next_weather(code)
        if data:
            hasil[nama] = data
        else:
            hasil[nama] = {"error": "Data tidak ditemukan"}
    return hasil
