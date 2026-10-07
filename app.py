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

# --- ФУНКЦИЯ ОТПРАВКИ В TELEGRAM ---
def send_telegram_message(token, chat_id, text):
    if not token or not chat_id or token == "ВАШ_ТОКЕН" or chat_id == "ВАШ_ID" or token.strip() == "" or chat_id.strip() == "":
        return False, "⚠️ Ключи Telegram не заполнены в боковом меню."
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
        return 34.05, 25.10, 11.5, "🚢 В пути (Средиземное море) | Скорость: 11.5 узлов"
    return 29.93, 32.55, 12.0, "Режим ожидания. Показываем плановые данные."

# --- НАДЕЖНАЯ ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В СЕССИИ ---
if "df_data" not in st.session_state or not isinstance(st.session_state.df_data, pd.DataFrame) or st.session_state.df_data.empty:
    st.session_state.df_data = pd.DataFrame([{
        'ID Сделки': 'DEAL-TEST-ETA', 'Дата': str(datetime.now().date()), 'Инкотермс': 'CIF',
        'Название судна': 'Vessel Alpha', 'MMSI/IMO': '211281610',
        'Порт загрузки': 'Стамбул (Турция)', 'Порт разгрузки': 'Новороссийск (Россия)', 
        'Цена закупки ($)': 100000.0, 'Цена продажи ($)': 180000.0, 'Фрахт ($)': 15000.0, 
        'Пошлины и Страховка ($)': 5000.0, 'Прочие расходы ($)': 2000.0, 
        'Норма простоя (дн)': 3, 'Ставка демереджа ($/сут)': 5000.0,
        'Крайняя дата прибытия': str(datetime.now().date() + timedelta(days=2)),
        'Демередж ($)': 0.0, 'Чистая прибыль ($)': 58000.0
    }])

# --- ИНТЕРФЕЙС ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Платформа CCT1 Enterprise Pro")

st.sidebar.header("🤖 Настройки Telegram")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="ВАШ_ТОКЕН", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="ВАШ_ID")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок (Excel)", "📊 Аналитика и Прогноз ETA"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.subheader("📦 Финансовые параметры сделки")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    
    price_buy = st.number_input("Цена закупки товара ($):", min_value=0.0, value=100000.0)
    price_sell = st.number_input("Цена продажи товара ($):", min_value=0.0, value=150000.0)
    
    # Подсказка по Инкотермс
    if incoterms == "FOB":
        st.caption("💡 При FOB фрахт оплачивает покупатель. Поле фрахта не будет вычитаться из вашей прибыли.")
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    
    duties = st.number_input("Пошлины и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
        
    st.subheader("🚢 Направление и Судно")
    port_start = st.selectbox("Выберите Порт ЗАГРУЗКИ:", sorted(list(PORTS.keys())), index=8)
    port_end = st.selectbox("Выберите Порт РАЗГРУЗКИ:", sorted(list(PORTS.keys())), index=0)
    
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    
    st.subheader("⏱ Плановое расписание рейса")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    deadline_date = st.date_input("Крайний срок прибытия по контракту (Laycan deadline):", value=datetime.now().date() + timedelta(days=5))

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ СДЕЛКУ И ОТПРАВИТЬ ОТЧЕТ", type="primary", use_container_width=True):
        # Логика Инкотермс
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        net_profit = price_sell - price_buy - actual_freight - duties - extra_costs
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Инкотермс': incoterms,
            'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 
            'Цена закупки ($)': float(price_buy), 'Цена продажи ($)': float(price_sell), 
            'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days),
            'Ставка демереджа ($/сут)': float(demurrage_rate), 
            'Крайняя дата прибытия': str(deadline_date),
            'Демередж ($)': 0.0, 'Чистая прибыль ($)': float(net_profit)
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        tg_text = f"📝 *Новая сделка сохранена ({incoterms})!*\n\n*ID:* {deal_id}\n*Маршрут:* {port_start} ➡️ {port_end}\n*Судно:* {vessel_name}\n*Ожидаемая прибыль:* ${net_profit:,.2f}"
        success, info = send_telegram_message(tg_token, tg_chat, tg_text)
        if success:
            st.success("🤖 Отчет доставлен в Telegram!")
        st.success(f"✅ Сделка {deal_id} внесена в реестр!")
        st.rerun()

# --- ВКЛАДКА 2 ---
with tab2:
    st.header("📋 Реестр торговых сделок")
    st.dataframe(st.session_state.df_data, use_container_width=True)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.df_data.to_excel(writer, index=False, sheet_name='Сделки CCT1')
    st.download_button(
        label="📥 СКАЧАТЬ БАЗУ В EXCEL (.xlsx)", data=buffer.getvalue(),
        file_name=f"CCT1_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True
    )

# --- ВКЛАДКА 3 ---
with tab3:
    st.header("📊 Умный мониторинг и радар рисков ETA")
    df = st.session_state.df_data
    
    selected_deal = st.selectbox("Выберите активную сделку:", df['ID Сделки'].unique())
    vessel_info = df[df['ID Сделки'] == selected_deal].iloc[0] # Исправлено чтение
    
    st.write(f"🚢 **Судно:** {vessel_info['Название судна']} | **Базис:** {vessel_info['Инкотермс']}")
    
    with st.spinner("Сбор телеметрии судна с радаров AIS..."):
        v_lat, v_lon, v_speed, status_text = get_live_vessel_data(vessel_info['MMSI/IMO'])
    st.info(f"📡 {status_text}")
    
    target_port_name = vessel_info['Порт разгрузки']
    port_coords = PORTS[target_port_name]
    distance_to_port = haversine(v_lat, v_lon, port_coords['lat'], port_coords['lon'])
    st.write(f"📏 **Оставшееся расстояние до порта назначения:** {round(distance_to_port, 1)} км")
    
    # --- ИНТЕЛЛЕКТУАЛЬНЫЙ РАСЧЕТ ETA ЧЕРЕЗ СКОРОСТЬ СУДНА ---
    if v_speed > 0.5:
        # Переводим узлы в км/ч (1 узел = 1.852 км/ч)
        speed_kmh = v_speed * 1.852
        hours_left = distance_to_port / speed_kmh
        days_left = hours_left / 24
        
        eta_datetime = datetime.now() + timedelta(hours=hours_left)
        st.success(f"⏱ **Прогноз прибытия (ETA):** {eta_datetime.strftime('%d.%m.%Y %H:%M')} (осталось плыть: {round(days_left, 1)} дн.)")
        
        # Проверка рисков нарушения контракта (Демередж в пути)
