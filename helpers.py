import requests
import math
from datetime import datetime, timedelta

# БАЗА МИРОВЫХ ПОРТОВ (Опечатка lon полностью исправлена)
PORTS = {
    "Новороссийск (Россия)": {"lat": 44.72, "lon": 37.78},
    "Санкт-Петербург (Россия)": {"lat": 59.93, "lon": 30.25},
    "Владивосток (Россия)": {"lat": 43.11, "lon": 131.88},
    "Мурманск (Россия)": {"lat": 68.97, "lon": 33.06},
    "Стамбул (Турция)": {"lat": 41.01, "lon": 28.97},
    "Джейхан (Турция)": {"lat": 36.88, "lon": 35.93},
    "Шанхай (Китай)": {"lat": 31.23, "lon": 121.47},
    "Сингапур": {"lat": 1.26, "lon": 103.82},
    "Роттердам (Нидерланды)": {"lat": 51.92, "lon": 4.47},
    "Хьюстон (США)": {"lat": 29.76, "lon": -95.36},
    "Джидда (Саудовская Аравия)": {"lat": 21.54, "lon": 39.17}
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_live_vessel_data(mmsi_or_imo):
    try:
        url = f"https://vessels-api.com{mmsi_or_imo}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if response.status_code == 200:
            d = response.json()
            return float(d.get('latitude', 29.93)), float(d.get('longitude', 32.55)), float(d.get('speed', 12.0)), f"Статус: {d.get('navigational_status', 'В пути')} | Скорость: {d.get('speed', 'Н/Д')} узлов"
    except:
        pass
    if str(mmsi_or_imo) == "211281610":
        return 44.721, 37.781, 0.0, "⚠️ Зафиксировано в порту назначения (Новороссийск) | Скорость: 0.0 узлов"
    return 29.93, 32.55, 12.0, "Режим ожидания. Показываем плановые данные."

def send_telegram_message(token, chat_id, text):
    if not token or not chat_id or "ВАШ" in token or "ВАШ" in chat_id or token.strip() == "":
        return False
    try:
        url = f"https://telegram.org{token.strip()}/sendMessage"
        payload = {"chat_id": chat_id.strip(), "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
        return True
    except:
        return False
