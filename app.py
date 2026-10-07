import streamlit as st
import pandas as pd
import requests
import math
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

# ---БАЗА МИРОВЫХ ПОРТОВ (Координаты для авторасчета) ---
PORTS = {
    "Новороссийск (Россия)": {"lat": 44.72, "lon": 37.78},
    "Санкт-Петербург (Россия)": {"lat": 59.93, "lon": 30.25},
    "Владивосток (Россия)": {"lat": 43.11, "lon": 131.88},
    "Шанхай (Китай)": {"lat": 31.23, "lon": 121.47},
    "Роттердам (Нидерланды)": {"lat": 51.92, "lon": 4.47},
    "Сингапур": {"lat": 1.26, "lon": 103.82},
    "Хьюстон (США)": {"lat": 29.76, "lon": -95.36},
    "Джидда (Саудовская Аравия)": {"lat": 21.54, "lon": 39.17},
    "Стамбул (Турция)": {"lat": 41.01, "lon": 28.97}
}

# Функция расчета расстояния между двумя точками на Земле (в километрах)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Радиус Земли
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- ФУНКЦИЯ ТРЕКИНГА AIS ---
def get_live_vessel_data(mmsi_or_imo):
    try:
        url = f"https://vessels-api.com{mmsi_or_imo}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = data.get('latitude', 29.93)
            lon = data.get('longitude', 32.55)
            status = data.get('navigational_status', 'В пути')
            speed = data.get('speed', 'Н/Д')
            return float(lat), float(lon), f"Статус: {status} | Скорость: {speed} узлов"
    except:
        pass
    # Если судно тест-драйвовое, сымитируем, что оно УЖЕ приплыло в Новороссийск и стоит там лишние дни
    if mmsi_or_imo == "211281610":
        return 44.722, 37.782, "⚠️ Стоит в порту разгрузки (Новороссийск) | Скорость: 0 узлов"
    return 29.93, 32.55, "Режим ожидания. Показываем плановую точку."

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В ПАМЯТИ ---
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
        'Пошлины ($)': 5000.0,
        'Прочие расходы ($)': 2000.0,
        'Норма простоя (дн)': 3,
        'Ставка демереджа ($/сут)': 5000.0,
        'Дата захода в порт': str(date(2026, 10, 1)), # Приплыл неделю назад
        'Демередж ($)': 15000.0, # 3 дня норма + 3 дня сверху = 15000$ штрафа
        'Чистая прибыль ($)': 33000.0
    }])

# --- ИНТЕРФЕЙС САЙТА ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Система CCT1 Smart-Logistics")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок", "📊 Аналитика и Авто-Демередж"])

# --- ВКЛАДКА 1: ВВОД ДАННЫХ ---
with tab1:
    st.subheader("📦 Расширенные параметры сделки")
    deal_id = st.text_input("Номер или ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    
    price_buy = st.number_input("Цена закупки товара ($):", min_value=0.0, value=100000.0)
    price_sell = st.number_input("Цена продажи товара ($):", min_value=0.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины, таможня и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
        
    st.subheader("🚢 Логистика и Маршрут")
    port_start = st.selectbox("Выберите Порт ЗАГРУЗКИ:", list(PORTS.keys()), index=8) # По умолчанию Стамбул
    port_end = st.selectbox("Выберите Порт РАЗГРУЗКИ:", list(PORTS.keys()), index=0) # По умолчанию Новороссийск
    
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна (9 цифр):", value="211281610")
    
    st.subheader("⏱ Условия демереджа")
    allowed_days = st.number_input("Нормативное время в порту на выгрузку (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    
    # Новое поле: когда судно физически бросило якорь в порту
    arrival_date = st.date_input("Дата фактического захода в порт (если уже зашло):", value=datetime.now().date())

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        # Первичный расчет демереджа по датам (если судно зашло раньше сегодняшнего дня)
        today = datetime.now().date()
        days_in_port = (today - arrival_date).days
        days_overdue = max(0, days_in_port - allowed_days)
        demurrage_total = days_overdue * demurrage_rate
        
        net_profit = price_sell - price_buy - freight - duties - extra_costs - demurrage_total
        
        new_row = {
            'ID Сделки': deal_id,
            'Дата': str(deal_date),
            'Название судна': vessel_name,
            'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start,
            'Порт разгрузки': port_end,
            'Цена закупки ($)': float(price_buy),
            'Цена продажи ($)': float(price_sell),
            'Фрахт ($)': float(freight),
            'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs),
            'Норма простоя (дн)': int(allowed_days),
            'Ставка демереджа ($/сут)': float(demurrage_rate),
            'Дата захода в порт': str(arrival_date),
            'Демередж ($)': float(demurrage_total),
            'Чистая прибыль ($)': float(net_profit)
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"✅ Сделка {deal_id} сохранена!")
        st.rerun()

# --- ВКЛАДКА 2: БАЗА СДЕЛОК ---
with tab2:
    st.header("Все зарегистрированные сделки")
    st.dataframe(st.session_state.df_data, use_container_width=True)
    
    st.write("---")
    delete_id = st.selectbox("ID для удаления:", st.session_state.df_data['ID Сделки'].unique())
    if st.button("❌ Удалить сделку", use_container_width=True):
        st.session_state.df_data = st.session_state.df_data[st.session_state.df_data['ID Сделки'] != delete_id]
        st.warning(f"Сделка {delete_id} удалена.")
        st.rerun()

# --- ВКЛАДКА 3: АНАЛИТИКА И АВТО-ДЕМЕРЕДЖ ---
with tab3:
    st.header("📈 Умная аналитика логистики")
    df = st.session_state.df_data
    
    selected_deal = st.selectbox("Выберите сделку для онлайн-проверки:", df['ID Сделки'].unique())
    vessel_info = df[df['ID Сделки'] == selected_deal].iloc[0]
    
    st.write(f"🚢 **Судно:** {vessel_info['Название судна']} | **Маршрут:** {vessel_info['Порт загрузки']} → {vessel_info['Порт разгрузки']}")
    
    # 1. ЗАПРОС К ЖИВЫМ СПУТНИКАМ
    with st.spinner("Связь со спутниками AIS..."):
        v_lat, v_lon, status_text = get_live_vessel_data(vessel_info['MMSI/IMO'])
    
    st.warning(f"📡 {status_text}")
    
    # 2. АВТОМАТИЧЕСКИЙ РАСЧЕТ РАССТОЯНИЯ ДО ПОРТА НАЗНАЧЕНИЯ
    target_port_name = vessel_info['Порт разгрузки']
    port_coords = PORTS[target_port_name]
    
    distance_to_port = haversine(v_lat, v_lon, port_coords['lat'], port_coords['lon'])
    st.write(f"📏 **Расстояние до причала разгрузки:** {round(distance_to_port, 1)} км")
    
    # 3. АВТО-ЛОГИКА НАЧИСЛЕНИЯ ДЕМЕРЕДЖА
    # Если судно подошло ближе чем на 15 км к порту назначения, считаем дни простоя автоматически
    if distance_to_port <= 15.0:
        st.info("🎯 Робот зафиксировал: судно находится внутри акватории порта разгрузки!")
        
        entry_date = datetime.strptime(str(vessel_info['Дата захода в порт']), "%Y-%m-%d").date()
        days_spent = (datetime.now().date() - entry_date).days
        overdue = max(0, days_spent - int(vessel_info['Норма простоя (дн)']))
        auto_demurrage = overdue * float(vessel_info['Ставка демереджа ($/сут)'])
        
        st.error(f"⏳ Дней в порту: {days_spent} | Превышение нормы на: {overdue} дн.")
        st.error(f"🚨 Автоматически начисленный демередж: **${auto_demurrage:,}**")
    else:
        st.success("🌊 Судно находится в открытом море на переходе. Демередж равен $0.")
    
    # 4. ВЫВОД КАРТЫ (Показываем и судно, и порт назначения)
    map_df = pd.DataFrame([
        {'latitude': float(v_lat), 'longitude': float(v_lon)}, # Корабль
        {'latitude': float(port_coords['lat']), 'longitude': float(port_coords['lon'])} # Порт
    ])
    st.map(map_df, zoom=4)
