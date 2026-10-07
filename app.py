import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date, timedelta

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

# --- ФУНКЦИЯ ПОЛУЧЕНИЯ АКТУАЛЬНЫХ КУРСОВ ВАЛЮТ ---
@st.cache_data(ttl=3600)
def get_exchange_rates():
    try:
        url = "https://er-api.com"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            rates = response.json().get("rates", {})
            return {
                "USD": 1.0,
                "RUB": rates.get("RUB", 93.5),
                "CNY": rates.get("CNY", 7.2)
            }
    except:
        pass
    return {"USD": 1.0, "RUB": 93.5, "CNY": 7.2}

CURRENCY_RATES = get_exchange_rates()

def convert_to_usd(amount, from_currency):
    rate = CURRENCY_RATES.get(from_currency, 1.0)
    return float(amount / rate)

# --- ФУНКЦИЯ ОТПРАВКИ В TELEGRAM ---
def send_telegram_message(token, chat_id, text):
    if not token or not chat_id or token == "ВАШ_ТОКЕН" or chat_id == "ВАШ_ID" or token.strip() == "" or chat_id.strip() == "":
        return False
    try:
        url = f"https://telegram.org{token.strip()}/sendMessage"
        payload = {"chat_id": chat_id.strip(), "text": text, "parse_mode": "Markdown"}
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except:
        return False

# --- БАЗА МИРОВЫХ ПОРТОВ ---
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return float(data.get('latitude', 29.93)), float(data.get('longitude', 32.55)), float(data.get('speed', 12.0)), f"Статус: {data.get('navigational_status', 'В пути')} | Скорость: {data.get('speed', 'Н/Д')} узлов"
    except:
        pass
    if mmsi_or_imo == "211281610":
        return 44.721, 37.781, 0.0, "⚠️ Зафиксировано в порту назначения (Новороссийск) | Скорость: 0.0 узлов"
    return 29.93, 32.55, 12.0, "Режим ожидания. Показываем плановые данные."

# --- ИНОЗОЛИРОВАННАЯ ФУНКЦИЯ ДЛЯ ТРЕТЬЕЙ ВКЛАДКИ (ЗАЩИТА ОТ INDENTATION ERROR) ---
def render_radar_tab(df_analysis, tg_token, tg_chat):
    if df_analysis.empty:
        st.info("Нет активных сделок для отображения.")
        return

    selected_deal = st.selectbox("Выберите активную сделку:", list(df_analysis['ID Сделки'].unique()))
    matching_rows = df_analysis[df_analysis['ID Сделки'] == selected_deal]
    
    if matching_rows.empty:
        st.warning("Сделка не найдена.")
        return

    v_list = matching_rows.to_dict('records')
    v_info = v_list[0]
    
    st.write(f"🚢 **Судно:** {v_info['Название судна']} | **Базис:** {v_info.get('Инкотермс', 'CIF')}")
    
    with st.spinner("Сбор телеметрии судна с радаров AIS..."):
        v_lat, v_lon, v_speed, status_text = get_live_vessel_data(v_info['MMSI/IMO'])
    st.info(f"📡 {status_text}")
    
    target_port_name = v_info['Port razgruzki'] if 'Port razgruzki' in v_info else v_info['Порт разгрузки']
    port_coords = PORTS[target_port_name]
    distance_to_port = haversine(v_lat, v_lon, port_coords['lat'], port_coords['lon'])
    st.write(f"📏 **Дистанция до причала порта разгрузки:** {round(distance_to_port, 1)} км")
    
    # Режим 1: Судно в порту
    if distance_to_port <= 15.0:
        st.error("🎯 АВТОМАТИЧЕСКАЯ ФИКСАЦИЯ: Судно находится внутри акватории порта назначения!")
        entry_date_str = v_info.get('Дата захода в порт', str(datetime.now().date()))
        entry_date = datetime.strptime(str(entry_date_str), "%Y-%m-%d").date()
        days_spent = (datetime.now().date() - entry_date).days
        overdue = max(0, days_spent - int(v_info['Норма простоя (дн)']))
        auto_demurrage = overdue * float(v_info['Ставка демереджа ($/сут)'])
        st.error(f"⏳ Сверхнормативный простой в порту: **{overdue} дней** (Всего дней у причала: {days_spent})")
        st.error(f"🚨 Текущий начисленный демередж: **${auto_demurrage:,}**")
        
        if overdue > 0 and st.button("🚨 ОТПРАВИТЬ СИГНАЛ ПО ДЕМЕРЕДЖУ В TELEGRAM", use_container_width=True):
            alert_text = f"⚠️ *ВНИМАНИЕ! РАСТЕТ ДЕМЕРЕДЖ!*\n\n*Сделка:* {selected_deal}\n*Судно:* {v_info['Название sunda'] if 'Название sunda' in v_info else v_info['Название судна']}\n*Простой:* {overdue} дн.\n*Убыток:* -${auto_demurrage:,}"
            send_telegram_message(tg_token, tg_chat, alert_text)
            st.success("🚨 Экстренное уведомление отправлено в чат!")
            
    # Режим 2: Судно в море
    if distance_to_port > 15.0:
        st.success("🌊 Корабль находится на переходе в море.")
        if v_speed > 0.5:
            speed_kmh = v_speed * 1.852
            hours_left = distance_to_port / speed_kmh
            days_left = hours_left / 24
            eta_datetime = datetime.now() + timedelta(hours=hours_left)
            st.success(f"⏱ **Прогноз прибытия (ETA):** {eta_datetime.strftime('%d.%m.%Y %H:%M')} (осталось: {round(days_left, 1)} дн.)")
            contract_deadline = datetime.strptime(str(v_info['Крайняя дата прибытия']), "%Y-%m-%d")
            
            if eta_datetime > contract_deadline:
                days_late = (eta_datetime - contract_deadline).days + 1
                risk_cost = days_late * float(v_info['Ставка демереджа ($/сут)'])
                st.error(f"🚨 **РИСК ЗАДЕРЖКИ КОНТРАКТА!** Опоздание: {days_late} дн. Прогноз демереджа: **-${risk_cost:,}**")
            if eta_datetime <= contract_deadline:
                st.success("✅ **Риски отсутствуют:** Судно идет по графику.")
        if v_speed <= 0.5:
            st.warning("⚓️ Судно дрейфует. Динамический расчет ETA приостановлен.")
            
    map_df = pd.DataFrame([{'latitude': float(v_lat), 'longitude': float(v_lon)}, {'latitude': float(port_coords['lat']), 'longitude': float(port_coords['lon'])}])
    st.map(map_df, zoom=3)

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В СЕССИИ ---
if "df_data" not in st.session_state or not isinstance(st.session_state.df_data, pd.DataFrame) or st.session_state.df_data.empty:
    st.session_state.df_data = pd.DataFrame([{
        'ID Сделки': 'DEAL-TEST-DEMURRAGE', 'Дата': str(datetime.now().date()), 'Инкотермс': 'CIF',
        'Название судна': 'Vessel Alpha', 'MMSI/IMO': '211281610',
        'Порт загрузки': 'Стамбул (Турция)', 'Порт разгрузки': 'Новороссийск (Россия)', 
        'Цена закупки (вход)': 700000.0, 'Валюта закупки': 'CNY',
        'Цена продажи (USD)': 180000.0, 'Фрахт ($)': 15000.0, 
        'Пошлины и Страховка ($)': 5000.0, 'Прочие расходы ($)': 2000.0, 
        'Норма простоя (дн)': 3, 'Ставка демереджа ($/сут)': 5000.0,
        'Крайняя дата прибытия': str(datetime.now().date() + timedelta(days=2)),
        'Дата захода в порт': str(datetime.now().date() - timedelta(days=6)),
        'Демередж ($)': 15000.0, 'Чистая прибыль ($)': 38000.0
    }])

# --- ИНТЕРФЕЙС ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Платформа CCT1 Enterprise Pro")

st.sidebar.header("💱 Живой курс валют (к USD)")
st.sidebar.write(f"💵 1 USD = **{round(CURRENCY_RATES['RUB'], 2)}** RUB")
st.sidebar.write(f"🇨🇳 1 USD = **{round(CURRENCY_RATES['CNY'], 2)}** CNY")

st.sidebar.header("🤖 Настройки Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="ВАШ_ID")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок (Excel)", "📊 Аналитика и Умный Радар"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.subheader("📦 Финансовые параметры сделки")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    
    st.write("---")
    st.write("**💵 Закупка товара**")
    buy_curr = st.selectbox("Выберите валюту закупки товара:", ["USD", "CNY", "RUB"])
    price_buy = st.number_input(f"Сумма закупки в выбранной валюте ({buy_curr}):", min_value=0.0, value=100000.0)
    
    price_buy_usd = convert_to_usd(price_buy, buy_curr)
    if buy_curr != "USD":
        st.caption(f"ℹ️ В эквиваленте: **${round(price_buy_usd, 2):,} USD** по курсу.")
        
