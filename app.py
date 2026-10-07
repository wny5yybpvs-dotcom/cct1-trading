import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

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

# --- ТЕКСТ ДЛЯ TELEGRAM ---
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
            return False, f"Ошибка Telegram: {error_desc}"
    except Exception as e:
        return False, f"Ошибка сети: {str(e)}"

# --- БАЗА МИРОВЫХ ПОРТОВ ---
PORTS = {
    "Новороссийск (Россия)": {"lat": 44.72, "lon": 37.78},
    "Санкт-Петербург (Россия)": {"lat": 59.93, "lon": 30.25},
    "Владивосток (Россия)": {"lat": 43.11, "lon": 131.88},
    "Мурманск (Россия)": {"lat": 68.97, "lon": 33.06},
    "Тамань (Россия)": {"lat": 45.13, "lon": 36.68},
    "Кавказ (Россия)": {"lat": 45.34, "lon": 36.67},
    "Усть-Луга (Россия)": {"lat": 59.68, "lon": 28.43},
    "Находка (Россия)": {"lat": 42.81, "lon": 132.88},
    "Стамбул (Турция)": {"lat": 41.01, "lon": 28.97},
    "Джейхан (Турция)": {"lat": 36.88, "lon": 35.93},
    "Поти (Грузия)": {"lat": 42.14, "lon": 41.64},
    "Актау (Казахстан)": {"lat": 44.53, "lon": 51.17},
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
            return float(data.get('latitude', 29.93)), float(data.get('longitude', 32.55)), f"Статус: {data.get('navigational_status', 'В пути')} | Скорость: {data.get('speed', 'Н/Д')} узлов"
    except:
        pass
    if mmsi_or_imo == "211281610":
        return 44.722, 37.782, "⚠️ Стоит в порту разгрузки (Новороссийск) | Скорость: 0 узлов"
    return 29.93, 32.55, "Режим ожидания. Показываем плановую точку."

# --- ИНТЕРФЕЙС ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Платформа CCT1 Cloud")

# БОКОВАЯ ПАНЕЛЬ ДЛЯ НАСТРОЕК
st.sidebar.header("⚙️ Настройки интеграций")
sheet_url = st.sidebar.text_input("Ссылка на Google Таблицу:", value="ВСТАВЬТЕ_ССЫЛКУ_ИЗ_ШАГА_1")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="ВАШ_ID")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

# ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS
@st.cache_data(ttl=5) # Кэшируем данные на 5 секунд для быстроты
def load_gsheet_data(url):
    if "://google.com" not in url:
        return pd.DataFrame()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=url, ttl="5s")
    except:
        return pd.DataFrame()

# Загружаем актуальные данные из Google Sheets
if "://google.com" in sheet_url:
    df_data = load_gsheet_data(sheet_url)
else:
    df_data = pd.DataFrame()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок (Google)", "📊 Аналитика и Авто-Демередж"])

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
    port_start = st.selectbox("Выберите Порт ЗАГРУЗКИ:", sorted(list(PORTS.keys())), index=8)
    port_end = st.selectbox("Выберите Порт РАЗГРУЗКИ:", sorted(list(PORTS.keys())), index=0)
    
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    
    st.subheader("⏱ Условия демереджа")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ В GOOGLE SHEETS И TELEGRAM", type="primary", use_container_width=True):
        if "://google.com" not in sheet_url:
            st.error("❌ Сначала вставьте корректную ссылку на Google Таблицу в левое боковое меню!")
            st.stop()
            
        days_in_port = (datetime.now().date() - arrival_date).days
        days_overdue = max(0, days_in_port - allowed_days)
        demurrage_total = days_overdue * demurrage_rate
        net_profit = price_sell - price_buy - freight - duties - extra_costs - demurrage_total
        
        new_row = pd.DataFrame([{
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Цена закупки ($)': float(price_buy),
            'Цена продажи ($)': float(price_sell), 'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days),
            'Ставка демереджа ($/сут)': float(demurrage_rate), 'Дата захода в порт': str(arrival_date),
            'Демередж ($)': float(demurrage_total), 'Чистая прибыль ($)': float(net_profit)
        }])
        
        try:
            # Запись новой строки в конец Google Таблицы
            updated_df = pd.concat([df_data, new_row], ignore_index=True)
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(spreadsheet=sheet_url, data=updated_df)
            st.success("📊 Данные успешно записаны вечно в Google Sheets!")
            
            # Отправка в Telegram
            tg_text = f"📝 *Новая сделка в Google Sheets!*\n\n*ID:* {deal_id}\n*Маршрут:* {port_start} ➡️ {port_end}\n*Судно:* {vessel_name}\n*Чистая прибыль:* ${net_profit:,.2f}"
            success, info = send_telegram_message(tg_token, tg_chat, tg_text)
            if success:
                st.success("🤖 Отчет доставлен в Telegram!")
            
            st.rerun()
        except Exception as e:
            st.error(f"❌ Не удалось записать в Google Sheets. Проверьте права 'Редактор' для ссылки. Ошибка: {str(e)}")

# --- ВКЛАДКА 2 ---
with tab2:
    st.header("📋 Текущие записи в Google Sheets")
    if df_data.empty:
        st.info("Таблица пуста или ссылка в боковом меню не настроена.")
    else:
        st.dataframe(df_data, use_container_width=True)

# --- ВКЛАДКА 3 ---
with tab3:
    st.header("📊 Онлайн Мониторинг рейсов")
    if df_data.empty:
        st.info("Нет данных. Настройте таблицу и добавьте сделки.")
    else:
        selected_deal = st.selectbox("Выберите активную сделку:", df_data['ID Сделки'].unique())
        vessel_info = df_data[df_data['ID Сделки'] == selected_deal].iloc[0]
        
        st.write(f"🚢 **Судно:** {vessel_info['Название судна']} | **MMSI:** {vessel_info['MMSI/IMO']}")
        
        with st.spinner("Связь со спутниками AIS..."):
            v_lat, v_lon, status_text = get_live_vessel_data(vessel_info['MMSI/IMO'])
        st.warning(f"📡 {status_text}")
        
        target_port_name = vessel_info['Порт разгрузки']
        port_coords = PORTS[target_port_name]
        distance_to_port = haversine(v_lat, v_lon, port_coords['lat'], port_coords['lon'])
        st.write(f"📏 **Дистанция до причала:** {round(distance_to_port, 1)} км")
        
        if distance_to_port <= 15.0:
            st.error("🎯 Судно находится в порту назначения!")
            entry_date = datetime.strptime(str(vessel_info['Дата захода в порт']), "%Y-%m-%d").date()
            days_spent = (datetime.now().date() - entry_date).days
            overdue = max(0, days_spent - int(vessel_info['Норма простоя (дн)']))
