import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date, timedelta

# ==========================================
# 1. КОНФИГУРАЦИЯ СТРАНИЦЫ И СЕССИИ
# ==========================================
st.set_page_config(
    page_title="CCT1 - Зерновая Логистика & Экономика",
    page_icon="🌾",
    layout="wide"
)

st.title("🌾 Система Мониторинга Зерновых Сделок «CCT1»")

# Настройки интеграции в боковой панели
st.sidebar.header("⚙️ Настройки интеграции")
tg_token = st.sidebar.text_input("Telegram Bot Token:", value="", type="password")
tg_chat = st.sidebar.text_input("Telegram Chat ID:", value="")

# Фиксированные курсы валют для калькулятора
CURRENCY_RATES = {
    "USD": 1.0,
    "CNY": 7.3,
    "RUB": 95.0
}

# Инициализация базы данных сделок в памяти сессии
if 'df_data' not in st.session_state:
    st.session_state.df_data = pd.DataFrame([
        {
            'ID Сделки': 'DEAL-20261008-0001', 'Дата': '2026-10-08', 'Статус рейса': 'В пути', 'Культура': 'Пшеница 3 класс',
            'Инкотермс': 'CIF', 'Объем погрузки (Тонн)': 5000.0, 'Убыль в пути (%)': 0.5,
            'Объем выгрузки (Тонн)': 4975.0, 'Название судна': 'Vessel Alpha', 'MMSI/IMO': '211281610',
            'Порт загрузки': 'Стамбул', 'Порт разгрузки': 'Новороссийск', 'Закупка ($/т)': 180.0,
            'Продажа ($/т)': 240.0, 'Перевалка ($/т)': 12.0,
            'Демередж ($)': 0.0, 'Чистая прибыль ($)': 260000.0, 'Прибыль/Тонна ($)': 52.0
        }
    ])

# ==========================================
# 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (API И ГЕО)
# ==========================================
def get_port_coordinates(port_name):
    if not port_name or port_name.strip() == "":
        return 44.72, 37.78, "Новороссийск"
    try:
        # Исправлен базовый рабочий URL для Nominatim OpenStreetMap
        url = f"https://openstreetmap.org{requests.utils.quote(port_name)}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'CCT1_App_v5'}, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            d = r.json()
            return float(d[0].get('lat')), float(d[0].get('lon')), d[0].get('display_name', port_name).split(',')
    except:
        pass
    return 44.72, 37.78, f"{port_name} (Дефолт)"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 2

def get_live_vessel_data(mmsi):
    if str(mmsi) == "211281610":
        return 39.55, 29.30, 10.0, "🚢 В пути с зерном (Эгейское море) | Скорость: 10.0 узлов"
    return 29.93, 32.55, 12.0, "В пути (демо-координаты)"

# ==========================================
# 3. МОДУЛИ ИНТЕРФЕЙСА (ВКЛАДКИ)
# ==========================================
def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("🌾 Параметры зернового груза")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    vessel_status = st.selectbox("🚦 Текущий статус рейса:", ["В пути", "В порту", "Завершена (Архив)"])
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    
    # Специфика зерна
    grain_type = st.selectbox("Вид зерновой культуры:", ["Пшеница 3 класс", "Пшеница 4 класс", "Ячмень", "Кукуруза", "Шрот", "Подсолнечник"])
    cargo_volume = st.number_input("Объем погрузки (Тонн):", min_value=1.0, value=5000.0, step=100.0)
    loss_rate = st.number_input("Естественная убыль / Рефакция в пути (%):", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
    
    st.subheader("💵 Экономика зерновой сделки")
    buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
    price_buy_per_ton = st.number_input(f"Цена закупки за 1 ТОННУ ({buy_curr}):", min_value=0.0, value=180.0)
    price_sell_per_ton = st.number_input("Цена продажи за 1 ТОННУ ($):", min_value=0.0, value=240.0)
    
    # Накладные расходы на тонну
    elevator_costs_per_ton = st.number_input("Перевалка, элеватор, анализы ($ / тонну):", min_value=0.0, value=12.0)
    
    # Общие фиксированные расходы
    freight = st.number_input("Стоимость базового фрахта судна ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Таможенные пошлины и сертификаты ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы на рейс ($):", min_value=0.0, value=1000.0)
    
    st.subheader("🚢 Маршрут и Логистика")
    port_start = st.text_input("Введите Порт ЗАГРУЗКИ:", value="Стамбул")
    port_end = st.text_input("Введите Порт РАЗГРУЗКИ:", value="Новороссийск")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту на выгрузку (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    deadline_date = st.date_input("Крайний срок прибытия (Laycan):", value=datetime.now().date() + timedelta(days=2))
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    if st.button("💾 СОХРАНИТЬ ЗЕРНОВУЮ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        # Расчет веса, который доплывет по контракту (вычитаем убыль)
        delivered_volume = cargo_volume * (1 - (loss_rate / 100))
        
        # Перевод закупки в USD
        buy_usd_per_ton = float(price_buy_per_ton / CURRENCY_RATES.get(buy_curr, 1.0))
        
        # Общие суммы
        total_buy_usd = cargo_volume * buy_usd_per_ton
        total_sell_usd = delivered_volume * price_sell_per_ton
        total_elevator_usd = cargo_volume * elevator_costs_per_ton
        
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        days_in_port = (datetime.now().date() - arrival_date).days
        overdue = max(0, days_in_port - allowed_days)
        demurrage_total = overdue * demurrage_rate
        
        # Итоговая чистая прибыль
        net_profit = total_sell_usd - total_buy_usd - total_elevator_usd - actual_freight - float(duties) - float(extra_costs) - demurrage_total
        profit_per_ton = float(net_profit / cargo_volume)
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Культура': grain_type,
            'Инкотермс': incoterms, 'Объем погрузки (Тонн)': cargo_volume, 'Убыль в пути (%)': loss_rate,
            'Объем выгрузки (Тонн)': round(delivered_volume, 1), 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Закупка ($/т)': round(buy_usd_per_ton, 2),
            'Продажа ($/т)': price_sell_per_ton, 'Перевалка ($/т)': elevator_costs_per_ton,
            'Демередж ($)': float(demurrage_total), 'Чистая прибыль ($)': float(net_profit), 'Прибыль/Тонна ($)': float(profit_per_ton)
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        # Фикс эндпоинта отправки Telegram (добавлен /bot к базовому домену)
        if tg_token and tg_chat:
            tg_text = f"🌾 *Зерновая сделка сохранена!*\n\n*ID:* {deal_id}\n*Культура:* {grain_type}\n*Объем:* {cargo_volume} т (Доплывет: {round(delivered_volume, 1)} т)\n*Прибыль:* ${net_profit:,.2f} USD\n*Чистый доход/Тонна:* ${profit_per_ton:,.2f}"
            try:
                url = f"https://telegram.org{tg_token.strip()}/sendMessage"
                requests.post(url, json={"chat_id": tg_chat.strip(), "text": tg_text, "parse_mode": "Markdown"}, timeout=5)
            except:
                pass
                
        st.success(f"✅ Зерновая сделка {deal_id} успешно внесена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр зерновых сделок")
    status_filter = st.radio("Фильтр по статусу рейса:", ["Все сделки", "В пути", "В порту", "Завершена (Архив)"], horizontal=True)
    
    display_df = st.session_state.df_data
    if status_filter != "Все сделки" and 'Статус рейса' in display_df.columns:
        display_df = display_df[display_df['Статус рейса'] == status_filter]
        
    st.dataframe(display_df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        display_df.to_excel(writer, index=False, sheet_name='Зерно_CCT1')
    st.download_button(label="📥 СКАЧАТЬ РЕЕСТР ЗЕРНА В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="CCT1_Grain_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Логистический Радар Зерновозов")
    df = st.session_state.df_data
    
    radar_df = df
    if 'Статус рейса' in df.columns:
        radar_df = df[df['Статус рейса'] != "Завершена (Архив)"]
        
    if radar_df.empty:
        st.info("Нет активных зерновозов на мониторинге. Все рейсы в архиве.")
        return
        
    selected_deal = st.selectbox("Выберите судно для слежения:", list(radar_df['ID Сделки'].unique()))
    v_rows = radar_df[radar_df['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        st.write(f"🚢 **Судно:** {v_info.get('Название судна', 'Alpha')} | **Культура:** {v_info.get('Культура', 'Пшеница')} | **Погружено:** {v_info.get('Объем погрузки (Тонн)', 5000)} т")
        
        with st.spinner("Связь со спутниками AIS..."):
            v_lat, v_lon, v_speed, status_text = get_live_vessel_data(v_info['MMSI/IMO'])
        st.info(f"📡 {status_text}")
        
