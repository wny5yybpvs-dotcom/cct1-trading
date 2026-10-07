import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, timedelta

# ==========================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (API И ГЕО)
# ==========================================
def get_port_coordinates(port_name):
    if not port_name or port_name.strip() == "":
        return 44.72, 37.78  # Дефолт: Новороссийск
    try:
        url = f"https://openstreetmap.org{requests.utils.quote(port_name)}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'CCT1_App_v6'}, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            d = r.json()
            return float(d[0].get('lat')), float(d[0].get('lon'))
    except:
        pass
    if "стамбул" in port_name.lower(): return 41.01, 28.97
    if "новороссийск" in port_name.lower(): return 44.72, 37.78
    return 44.72, 37.78

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Радиус Земли в км
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 2

def get_live_vessel_data(mmsi):
    """
    Получает РЕАЛЬНЫЕ координаты судна БЕЗ КЛЮЧЕЙ И РЕГИСТРАЦИИ через открытый веб-шлюз.
    """
    clean_mmsi = str(mmsi).strip()
    if not clean_mmsi or clean_mmsi == "None":
        return 44.72, 37.78, 0.0, "❌ MMSI судна не указан"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(f"https://vesselfinder.com{clean_mmsi}", headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            lat = float(data.get("lat", data.get("latitude")))
            lon = float(data.get("lon", data.get("longitude")))
            speed = float(data.get("speed", data.get("sog", 0.0)))
            course = data.get("course", data.get("cog", "N/A"))
            vessel_status = data.get("status", "В пути")
            
            return lat, lon, speed, f"🛰️ Живые спутниковые данные AIS | Скорость: {speed} узлов | Курс: {course}° | Статус: {vessel_status}"
    except:
        pass

    # Резервный демо-режим для демонстрационной сделки
    if clean_mmsi == "211281610":
        return 39.55, 29.30, 10.0, "🚢 [DEMO] Vessel Alpha (Эгейское море) | Скорость: 10.0 узлов"
    return 43.50, 36.20, 12.0, "🚢 [DEMO] Автономный фолбэк-режим (Черное море)"

# ==========================================
# 2. МОДУЛИ ИНТЕРФЕЙСА (ВКЛАДКИ)
# ==========================================
def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("🌾 Параметры зернового груза")
    
    col1, col2 = st.columns(2)
    with col1:
        deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
        vessel_status = st.selectbox("🚦 Текущий статус рейса:", ["В пути", "В порту", "Завершена (Архив)"])
        incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    with col2:
        deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
        cargo_volume = st.number_input("Объем погрузки (Тонн):", min_value=1.0, value=5000.0, step=100.0)
    
    st.subheader("💵 Экономика зерновой сделки")
    col3, col4 = st.columns(2)
    with col3:
        buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
        price_buy_total = st.number_input(f"ОБЩАЯ стоимость закупки груза ({buy_curr}):", min_value=0.0, value=700000.0)
    with col4:
        price_sell_total = st.number_input("ОБЩАЯ стоимость продажи груза ($ USD):", min_value=0.0, value=180000.0)
    
    st.subheader("🚢 Логистика, Сроки и Накладные расходы")
    col5, col6 = st.columns(2)
    with col5:
        port_start = st.text_input("Порт ЗАГРУЗКИ:", value="Стамбул")
        port_end = st.text_input("Порт РАЗГРУЗКИ:", value="Новороссийск")
        vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
        vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    with col6:
        freight = st.number_input("Стоимость фрахта сусна ($):", min_value=0.0, value=15000.0)
        duties = st.number_input("Пошлины, Страховка и Сертификаты ($):", min_value=0.0, value=5000.0)
        extra_costs = st.number_input("Прочие накладные расходы на рейс ($):", min_value=0.0, value=2000.0)
        allowed_days = st.number_input("Норма простоя на выгрузку (дней):", min_value=1, value=3)
        demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    
    col7, col8 = st.columns(2)
    with col7:
        deadline_date = st.date_input("Крайняя дата прибытия (Laycan):", value=datetime.now().date() + timedelta(days=2))
    with col8:
        arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date() - timedelta(days=6))

    if st.button("💾 СОХРАНИТЬ ЗЕРНОВУЮ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        buy_usd_total = float(price_buy_total / CURRENCY_RATES.get(buy_curr, 1.0))
        
        days_in_port = (datetime.now().date() - arrival_date).days
        overdue = max(0, days_in_port - allowed_days)
        demurrage_total = overdue * float(demurrage_rate)
        
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        
        net_profit = float(price_sell_total) - buy_usd_total - actual_freight - float(duties) - float(extra_costs) - demurrage_total
        profit_per_ton = float(net_profit / cargo_volume)
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Инкотермс': incoterms,
            'Объем (Тонн)': cargo_volume, 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 
            'Цена закупки (вход)': price_buy_total, 'Валюта закупки': buy_curr, 'Цена продажи (USD)': price_sell_total, 
            'Фрахт ($)': actual_freight, 'Пошлины и Страховка ($)': float(duties), 'Прочие расходы ($)': float(extra_costs), 
            'Норма простоя (дн)': allowed_days, 'Ставка демереджа ($/сут)': float(demurrage_rate),
            'Крайняя дата прибытия': str(deadline_date), 'Дата захода в порт': str(arrival_date),
            'Демередж ($)': demurrage_total, 'Чистая прибыль ($)': round(net_profit, 2), 'Прибыль/Тонна ($)': round(profit_per_ton, 2)
        }
        
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        if tg_token and tg_token != "ВАШ_ТОКЕН" and tg_chat and tg_chat != "ВАШ_ID":
            tg_text = f"🌾 *Новая зерновая сделка сохранена!*\n\n*ID:* {deal_id}\n*Судно:* {vessel_name}\n*Объем:* {cargo_volume} т\n*Чистая Прибыль:* ${net_profit:,.2f} USD\n*Демередж:* ${demurrage_total:,.2f} USD"
            try:
                url = f"https://telegram.org{tg_token.strip()}/sendMessage"
                requests.post(url, json={"chat_id": tg_chat.strip(), "text": tg_text, "parse_mode": "Markdown"}, timeout=5)
            except:
                pass
                
        st.success(f"✅ Зерновая сделка {deal_id} успешно сохранена!")
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
        display_df.to_excel(writer, index=False, sheet_name='CCT1_Trading')
    st.download_button(
        label="📥 СКАЧАТЬ РЕЕСТР В EXCEL (.xlsx)", 
        data=buffer.getvalue(), 
        file_name="CCT1_Global_Report.xlsx", 
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        use_container_width=True
    )

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Логистический Радар Зерновозов")
    df = st.session_state.df_data
    
    radar_df = df[df['Статус рейса'] != "Завершена (Архив)"] if 'Статус рейса' in df.columns else df
        
    if radar_df.empty:
        st.info("Нет активных зерновозов на мониторинге. Все рейсы в архиве.")
        return
        
    selected_deal = st.selectbox("Выберите судно для трекинга:", list(radar_df['ID Сделки'].unique()))
    v_rows = radar_df[radar_df['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        st.markdown(f"### 🚢 Мониторинг судна: `{v_info.get('Название судна', 'Alpha')}`")
        st.caption(f"MMSI/IMO: {v_info.get('MMSI/IMO')} | Базис: {v_info.get('Инкотермс')} | Объем: {v_info.get('Объем (Тонн)', 0)} т.")

        with st.spinner("Запрос спутниковых координат AIS..."):
            v_lat, v_lon, v_speed, status_text = get_live_vessel_data(v_info.get('MMSI/IMO'))
            p_end_lat, p_end_lon = get_port_coordinates(v_info.get('Порт разгрузки', 'Новороссийск'))
        
        st.success(status_text)
        
        distance_left = haversine(v_lat, v_lon, p_end_lat, p_end_lon)
        
        if v_speed > 0:
            speed_kmh = v_speed * 1.852
            hours_left = distance_left / speed_kmh
            eta_text = f"~ {round(hours_left / 24, 1)} дн. ({round(hours_left)} ч.)" if hours_left > 24 else f"~ {round(hours_left, 1)} ч."
        else:
            eta_text = "Судно на якоре / в порту"

        col_m1, col_m2, col_m3 = st.columns(3)
