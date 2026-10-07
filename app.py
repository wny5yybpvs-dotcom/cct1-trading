import streamlit as st
import pandas as pd
import requests
from datetime import datetime

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

# --- ФУНКЦИЯ АВТОМАТИЧЕСКОГО ТРЕКИНГА (БЕЗ РЕГИСТРАЦИИ) ---
def get_live_vessel_data(mmsi_or_imo):
    # Пытаемся постучаться в открытый демо-шлюз Vessels-API
    try:
        # Эндпоинт для поиска позиции по MMSI
        url = f"https://vessels-api.com{mmsi_or_imo}"
        # Для симуляции запроса от браузера
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            lat = data.get('latitude', 29.93)
            lon = data.get('longitude', 32.55)
            status = data.get('navigational_status', 'В пути / На связи')
            speed = data.get('speed', 'Н/Д')
            return float(lat), float(lon), f"Статус: {status} | Скорость: {speed} узлов"
    except:
        pass
    
    # Если лимиты демо-версии исчерпаны или судно вне зоны береговых радаров — выдаем базовую точку
    return 29.93, 32.55, "Режим ожидания. Показываем плановую точку (Суэцкий канал)."

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ В ПАМЯТИ ---
if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame([{
        'ID Сделки': 'Тест-01',
        'Дата': str(datetime.now().date()),
        'Название судна': 'Vessel Alpha',
        'MMSI/IMO': '211281610',
        'Цена закупки ($)': 100000.0,
        'Цена продажи ($)': 170000.0,
        'Фрахт ($)': 15000.0,
        'Пошлины и Страховка ($)': 5000.0,
        'Прочие расходы ($)': 2000.0,
        'Норма простоя (дн)': 3,
        'Ставка демереджа ($/сут)': 5000.0,
        'Дней простоя сверх нормы': 0,
        'Демередж ($)': 0.0,
        'Чистая прибыль ($)': 48000.0
    }])

# --- ИНТЕРФЕЙС САЙТА ---
st.set_page_config(layout="centered", page_title="CCT1 Trading & Logistics")
st.title("🚢 Система CCT1 Pro-Авто")

if st.sidebar.button("Выйти из системы"):
    st.session_state.auth = False
    st.rerun()

tab1, tab2, tab3 = st.tabs(["📥 Ввод данных", "📋 База сделок", "📊 Аналитика и Карта"])

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
        
    st.subheader("🚢 Логистика и Демередж")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна (9 цифр):", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=0, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    days_overdue = st.number_input("Фактический простой сверх нормы (дней):", min_value=0, value=0)

    st.write("---")
    
    if st.button("💾 СОХРАНИТЬ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        demurrage_total = days_overdue * demurrage_rate
        net_profit = price_sell - price_buy - freight - duties - extra_costs - demurrage_total
        
        new_row = {
            'ID Сделки': deal_id,
            'Дата': str(deal_date),
            'Название судна': vessel_name,
            'MMSI/IMO': vessel_mmsi,
            'Цена закупки ($)': float(price_buy),
            'Цена продажи ($)': float(price_sell),
            'Фрахт ($)': float(freight),
            'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs),
            'Норма простоя (дн)': int(allowed_days),
            'Ставка демереджа ($/сут)': float(demurrage_rate),
            'Дней простоя сверх нормы': int(days_overdue),
            'Демередж ($)': float(demurrage_total),
            'Чистая прибыль ($)': float(net_profit)
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"✅ Сделка {deal_id} успешно сохранена!")
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

# --- ВКЛАДКА 3: АНАЛИТИКА И КАРТА ---
with tab3:
    st.header("📈 Финансовые итоги")
    df = st.session_state.df_data
    
    st.metric("Всего сделок в списке", len(df))
    st.metric("Общий демередж", f"${df['Демередж ($)'].astype(float).sum():,}")
    st.metric("ОБЩАЯ ЧИСТАЯ ПРИБЫЛЬ", f"${df['Чистая прибыль ($)'].astype(float).sum():,}")
    
    st.write("### Прибыль по сделкам")
    chart_data = df.set_index('ID Сделки')['Чистая прибыль ($)'].astype(float)
    st.bar_chart(chart_data)
    
    st.write("---")
    st.subheader("🛰 Спутниковый трекинг")
    
    selected_deal = st.selectbox("Выберите сделку для слежения:", df['ID Сделки'].unique())
    vessel_info = df[df['ID Сделки'] == selected_deal].iloc[0]
    
    st.write(f"🚢 **Судно:** {vessel_info['Название судна']} | **MMSI:** {vessel_info['MMSI/IMO']}")
    
    # Автоматический запрос координат БЕЗ ввода ключей
    with st.spinner("Получение спутниковых данных AIS..."):
        lat, lon, status_text = get_live_vessel_data(vessel_info['MMSI/IMO'])
    
    st.info(f"📡 **Текущий статус:** {status_text}")
    
    # Строим карту
    map_df = pd.DataFrame([{'latitude': float(lat), 'longitude': float(lon)}])
    st.map(map_df, zoom=4)
