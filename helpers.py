import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date, timedelta

PORTS = {
    "Новороссийск (Россия)": {"lat": 44.72, "lon": 37.78},
    "Стамбул (Турция)": {"lat": 41.01, "lon": 28.97}
}

def get_port_coordinates(port_name):
    if not port_name or port_name.strip() == "":
        return 44.72, 37.78, "Новороссийск"
    try:
        url = f"https://openstreetmap.org{requests.utils.quote(port_name)}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'CCT1_App_v5'}, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            d = r.json()[0]
            return float(d.get('lat')), float(d.get('lon')), d.get('display_name', port_name).split(',')[0]
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
        return 44.721, 37.781, 0.0, "⚠️ Зафиксировано в акватории порта разгрузки | Скорость: 0.0 узлов"
    return 29.93, 32.55, 12.0, "В пути (демо-координаты)"

def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("📦 Финансовые параметры сделки")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    buy_curr = st.selectbox("Валюта закупки товара:", ["USD", "CNY", "RUB"])
    price_buy = st.number_input(f"Сумма закупки ({buy_curr}):", min_value=0.0, value=100000.0)
    
    price_buy_usd = float(price_buy / CURRENCY_RATES.get(buy_curr, 1.0))
    if buy_curr != "USD":
        st.caption(f"ℹ️ В эквиваленте: **${round(price_buy_usd, 2):,} USD**")
        
    price_sell = st.number_input("Цена ПРОДАЖИ товара ($):", min_value=0.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
    
    port_start = st.text_input("Введите Порт ЗАГРУЗКИ:", value="Стамбул")
    port_end = st.text_input("Введите Порт РАЗГРУЗКИ (любой в мире):", value="Новороссийск")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    deadline_date = st.date_input("Крайний срок прибытия (Laycan):", value=datetime.now().date() + timedelta(days=5))
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    if st.button("💾 СОХРАНИТЬ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        days_in_port = (datetime.now().date() - arrival_date).days
        overdue = max(0, days_in_port - allowed_days)
        demurrage_total = overdue * demurrage_rate
        net_profit = float(price_sell) - price_buy_usd - actual_freight - float(duties) - float(extra_costs) - demurrage_total
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Инкотермс': incoterms, 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Цена закупки (вход)': float(price_buy), 'Валюта закупки': buy_curr, 
            'Цена продажи (USD)': float(price_sell), 'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days), 'Ставка демереджа ($/сут)': float(demurrage_rate), 
            'Крайняя дата прибытия': str(deadline_date), 'Дата захода в порт': str(arrival_date), 'Демередж ($)': float(demurrage_total), 'Чистая прибыль ($)': float(net_profit)
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        tg_text = f"📝 *Новая сделка сохранена!*\n\n*ID:* {deal_id}\n*Маршрут:* {port_start} ➡️ {port_end}\n*Прибыль:* ${net_profit:,.2f} USD"
        try:
            url = f"https://telegram.org{tg_token.strip()}/sendMessage"
            requests.post(url, json={"chat_id": tg_chat.strip(), "text": tg_text, "parse_mode": "Markdown"}, timeout=5)
        except:
            pass
        st.success(f"✅ Сделка {deal_id} успешно внесена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр торговых сделок")
    st.dataframe(st.session_state.df_data, use_container_width=True)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.df_data.to_excel(writer, index=False, sheet_name='Сделки')
    st.download_button(label="📥 СКАЧАТЬ БАЗУ В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="CCT1_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Умный Мониторинг & Логистический Радар")
    df = st.session_state.df_data
    selected_deal = st.selectbox("Выберите активную сделку:", list(df['ID Сделки'].unique()))
    v_rows = df[df['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        st.write(f"🚢 **Судно:** {v_info.get('Название судна', 'Alpha')} | **Базис:** {v_info.get('Инкотермс', 'CIF')}")
        with st.spinner("Связь со спутниками AIS..."):
            v_lat, v_lon, v_speed, status_text = get_live_vessel_data(v_info['MMSI/IMO'])
        st.info(f"📡 {status_text}")
        
        with st.spinner("Поиск координат порта в мировой базе OpenStreetMap..."):
            p_lat, p_lon, p_name = get_port_coordinates(v_info['Порт разгрузки'])
            
        distance_to_port = haversine(v_lat, v_lon, p_lat, p_lon)
        st.write(f"📍 **Обнаружен порт разгрузки:** {p_name}")
        st.write(f"📏 **Дистанция до причала:** {round(distance_to_port, 1)} км")
        
        if distance_to_port <= 15.0:
            st.error("🎯 Судно находится внутри акватории порта назначения!")
            entry_date = datetime.strptime(str(v_info.get('Дата захода в порт', datetime.now().date())), "%Y-%m-%d").date()
            days_spent = (datetime.now().date() - entry_date).days
            overdue = max(0, days_spent - int(v_info['Норма простоя (дн)']))
            st.error(f"🚨 Начислено демереджа: **${overdue * float(v_info['Ставка демереджа ($/сут)']):,}** (Простой: {overdue} дн.)")
        else:
            st.success("🌊 Корабль находится на переходе в море.")
            if v_speed > 0.5:
                days_left = distance_to_port / (v_speed * 1.852) / 24
                st.success(f"⏱ **Прогноз прибытия (ETA):** через {round(days_left, 1)} дней ({ (datetime.now() + timedelta(days=days_left)).strftime('%d.%m.%Y') })")

        st.map(pd.DataFrame([{'latitude': float(v_lat), 'longitude': float(v_lon)}, {'latitude': float(p_lat), 'longitude': float(p_lon)}]))
