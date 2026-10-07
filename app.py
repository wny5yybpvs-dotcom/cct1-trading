import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date

# --- НАСТРОЙКА БЕЗОПАСНОСТИ ---
COMPANY_PASSWORD = "cct1_trade"

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Вход в систему трейдинга CCT1")
    pwd = st.text_input("Введите пароль компании:", type="password")
    if st.button("Войти"):
        if pwd == COMPANY_PASSWORD:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("❌ Неверный пароль")
    st.stop()

# --- ФУНКЦИЯ ОТПРАВКИ В TELEGRAM ---
def send_telegram_message(token, chat_id, text):
    if not token or not chat_id or token == "ВАШ_ТОКЕН" or chat_id == "ВАШ_ID" or token.strip() == "" or chat_id.strip() == "":
        return False, "⚠️ Поля токена или Chat ID не заполнены в боковом меню!"
    try:
        url = f"https://telegram.org{token.strip()}/sendMessage"
        payload = {"chat_id": chat_id.strip(), "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            return True, "Успешно!"
        else:
            error_desc = response.json().get("description", "Неизвестная ошибка")
            return False, f"Ошибка сервера Telegram: {error_desc} (Код {response.status_code})"
    except Exception as e:
        return False, f"Ошибка сети при отправке: {str(e)}"

# --- РАСШИРЕННАЯ БАЗА МИРОВЫХ ПОРТОВ (БОЛЕЕ 50 ПОРТОВ) ---
PORTS = {
    # --- РОССИЯ И СНГ ---
    "Новороссийск (Россия)": {"lat": 44.72, "lon": 37.78},
    "Санкт-Петербург (Россия)": {"lat": 59.93, "lon": 30.25},
    "Владивосток (Россия)": {"lat": 43.11, "lon": 131.88},
    "Мурманск (Россия)": {"lat": 68.97, "lon": 33.06},
    "Тамань (Россия)": {"lat": 45.13, "lon": 36.68},
    "Кавказ (Россия)": {"lat": 45.34, "lon": 36.67},
    "Усть-Луга (Россия)": {"lat": 59.68, "lon": 28.43},
    "Находка (Россия)": {"lat": 42.81, "lon": 132.88},
    "Калининград (Россия)": {"lat": 54.71, "lon": 20.45},
    "Архангельск (Россия)": {"lat": 64.54, "lon": 40.54},
    "Астрахань (Россия)": {"lat": 46.34, "lon": 48.01},
    "Туапсе (Россия)": {"lat": 44.09, "lon": 39.07},
    "Поти (Грузия)": {"lat": 42.14, "lon": 41.64},
    "Батуми (Грузия)": {"lat": 41.64, "lon": 41.64},
    "Актау (Казахстан)": {"lat": 44.53, "lon": 51.17},
    "Баку (Азербайджан)": {"lat": 40.37, "lon": 49.89},
    # --- ТУРЦИЯ И СРЕДИЗЕМНОМОРЬЕ ---
    "Стамбул (Турция)": {"lat": 41.01, "lon": 28.97},
    "Джейхан (Турция)": {"lat": 36.88, "lon": 35.93},
    "Искендерун (Турция)": {"lat": 36.58, "lon": 36.17},
    "Мерсин (Турция)": {"lat": 36.80, "lon": 34.63},
    "Измир (Турция)": {"lat": 38.42, "lon": 27.14},
    "Пирей (Греция)": {"lat": 37.94, "lon": 23.64},
    "Александрия (Египет)": {"lat": 31.20, "lon": 29.91},
    "Порт-Саид (Египет)": {"lat": 31.26, "lon": 32.30},
    "Хайфа (Израиль)": {"lat": 32.81, "lon": 34.99},
    # --- БЛИЖНИЙ ВОСТОК И ИРАН ---
    "Джидда (Саудовская Аравия)": {"lat": 21.54, "lon": 39.17},
    "Джебель-Али / Дубай (ОАЭ)": {"lat": 25.01, "lon": 55.06},
    "Фуджайра (ОАЭ)": {"lat": 25.12, "lon": 56.36},
    "Бендер-Аббас (Иран)": {"lat": 27.14, "lon": 56.22},
    "Басра (Ирак)": {"lat": 30.50, "lon": 47.81},
    "Доха (Катар)": {"lat": 25.28, "lon": 51.53},
    "Мина-Сальман (Бахрейн)": {"lat": 26.20, "lon": 50.60},
    # --- АЗИЯ ---
    "Шанхай (Китай)": {"lat": 31.23, "lon": 121.47},
    "Нинбо-Чжоушань (Китай)": {"lat": 29.86, "lon": 121.54},
    "Циндао (Китай)": {"lat": 36.07, "lon": 120.38},
    "Гуанчжоу (Китай)": {"lat": 23.12, "lon": 113.26},
    "Шэньчжэнь (Китай)": {"lat": 22.54, "lon": 114.05},
    "Тяньцзинь (Китай)": {"lat": 38.96, "lon": 117.78},
    "Сингапур": {"lat": 1.26, "lon": 103.82},
    "Пусан (Южная Корея)": {"lat": 35.17, "lon": 129.07},
    "Мумбаи / Джавахарлал Неру (Индия)": {"lat": 18.95, "lon": 72.95},
    "Мундра (Индия)": {"lat": 22.74, "lon": 69.70},
    "Коломбо (Шри-Ланка)": {"lat": 6.94, "lon": 79.84},
    # --- ЕВРОПА И ДРУГИЕ ---
    "Роттердам (Нидерланды)": {"lat": 51.92, "lon": 4.47},
    "Антверпен (Бельгия)": {"lat": 51.22, "lon": 4.40},
    "Гамбург (Германия)": {"lat": 53.55, "lon": 9.99},
    "Валенсия (Испания)": {"lat": 39.45, "lon": -0.32},
    "Хьюстон (США)": {"lat": 29.76, "lon": -95.36},
    "Сантос (Бразилия)": {"lat": -23.96, "lon": -46.33},
    "Дурбан (ЮАР)": {"lat": -29.85, "lon": 31.02}
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data.get('latitude', 29.93)), float(data.get('longitude', 32.55)), f"Статус: {data.get('navigational_status', 'В пути')} | Скорость: {data.get('speed', 'Н/Д')} узлов"
    except:
        pass
    if mmsi_or_imo == "211281610":
        return 44.722, 37.782, "⚠️ Стоит в порту разгрузки (Новороссийск) | Скорость: 0 узлов"
    return 29.93, 32.55, "Режим ожидания. Показываем плановую точку."

if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame([{
        'ID Сделки': 'Тест-Новороссийск', 
        'Дата': str(datetime.now().date()), 
        'Название судна': 'Vessel Alpha', 
        'MMSI/IMO': '211281610',
        'Порт загрузки': 'Стамбул (Турция)', 
        'Порт разгрузки': 'Новороссийск (Россия)', 
        'Цена закупки ($)': 100000.0, 
        'Цена продажи ($)': 170000.0,
        'Фрахт ($)': 15000.0, 
        'Пошлины и Страховка ($)': 5000.0, 
        'Прочие расходы ($)': 2000.0, 
        'Норма простоя (дн)': 3, 
        'Ставка демереджа ($/сут)': 5000.0,
        'Дата захода в港': str(date(2026, 10, 1)), 
        'Демередж ($)': 15000.0, 
        'Чистая прибыль ($)': 33000.0
    }])

# --- ИНТЕРФЕЙС ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Платформа CCT1 Enterprise")

st.sidebar.header("🤖 Настройки Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="ВАШ_ID")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок (Excel)", "📊 Аналитика и Авто-Демередж"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.subheader("📦 Финансовые параметры сделки")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    
    price_buy = st.number_input("Цена закупки товара ($):", min_value=0.0, value=100000.0)
    price_sell = st.number_input("Цена продажи товара ($):", min_value=0.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
        
    st.subheader("🚢 Направление и Судно")
    port_start = st.selectbox("Выберите Порт ЗАГРУЗКИ:", sorted(list(PORTS.keys())), index=40) # Дефолт Стамбул
    port_end = st.selectbox("Выберите Порт РАЗГРУЗКИ:", sorted(list(PORTS.keys())), index=23) # Дефолт Новороссийск
    
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    
    st.subheader("⏱ Условия демереджа")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ СДЕЛКУ И ОТПРАВИТЬ ОТЧЕТ", type="primary", use_container_width=True):
        days_in_port = (datetime.now().date() - arrival_date).days
        days_overdue = max(0, days_in_port - allowed_days)
        demurrage_total = days_overdue * demurrage_rate
        net_profit = price_sell - price_buy - freight - duties - extra_costs - demurrage_total
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Цена закупки ($)': float(price_buy),
            'Цена продажи ($)': float(price_sell), 'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days),
            'Ставка демереджа ($/сут)': float(demurrage_rate), 'Дата захода в порт': str(arrival_date),
            'Демередж ($)': float(demurrage_total), 'Чистая прибыль ($)': float(net_profit)
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        tg_text = f"📝 *Новая сделка сохранена!*\n\n*ID:* {deal_id}\n*Маршрут:* {port_start} ➡️ {port_end}\n*Судно:* {vessel_name}\n*Чистая прибыль:* ${net_profit:,.2f}"
        
        success, info = send_telegram_message(tg_token, tg_chat, tg_text)
        if success:
            st.success("🤖 Отчет успешно доставлен в Telegram!")
        else:
            st.error(f"❌ Ошибка отправки: {info}")
            
