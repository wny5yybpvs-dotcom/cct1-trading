import streamlit as st
import pandas as pd
import requests
import math
import io
from datetime import datetime, date, timedelta

def get_port_coordinates(port_name):
    if not port_name or port_name.strip() == "":
        return 44.72, 37.78, "Новороссийск"
    try:
        url = f"https://openstreetmap.org{requests.utils.quote(port_name)}&format=json&limit=1"
        r = requests.get(url, headers={'User-Agent': 'CCT1_App_v5'}, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            d = r.json()
            return float(d.get('lat')), float(d.get('lon')), d.get('display_name', port_name).split(',')
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
        return 39.55, 29.30, 10.0, "🚢 В пути (Эгейское море) | Скорость: 10.0 узлов"
    return 29.93, 32.55, 12.0, "В пути (демо-координаты)"

def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("📦 Финансовые параметры и Объем")
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    
    # ШАГ 3: Выбор статуса сделки при вводе
    vessel_status = st.selectbox("🚦 Текущий статус рейса:", ["В пути", "В порту", "Завершена (Архив)"])
    
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    
    # ШАГ 2: Грузовой калькулятор (Объем в тоннах)
    cargo_volume = st.number_input("Объем груза (Тонн):", min_value=1.0, value=5000.0, step=100.0)
    
    buy_curr = st.selectbox("Валюта закупки товара (за тонну или общая):", ["USD", "CNY", "RUB"])
    price_buy_total = st.number_input(f"ОБЩАЯ сумма закупки товара ({buy_curr}):", min_value=0.0, value=100000.0)
    
    price_buy_usd = float(price_buy_total / CURRENCY_RATES.get(buy_curr, 1.0))
    if buy_curr != "USD":
        st.caption(f"ℹ️ Закупка в эквиваленте: **${round(price_buy_usd, 2):,} USD**")
        
    price_sell = st.number_input("ОБЩАЯ цена продажи товара ($):", min_value=0.0, value=150000.0)
    freight = st.number_input("Стоимость базового фрахта ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины и страхование ($):", min_value=0.0, value=3000.0)
    extra_costs = st.number_input("Прочие накладные расходы ($):", min_value=0.0, value=1000.0)
    
    st.subheader("🚢 Маршрут и Логистика")
    port_start = st.text_input("Введите Порт ЗАГРУЗКИ:", value="Стамбул")
    port_end = st.text_input("Введите Порт РАЗГРУЗКИ:", value="Новороссийск")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    allowed_days = st.number_input("Нормативное время в порту (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    deadline_date = st.date_input("Крайний срок прибытия (Laycan):", value=datetime.now().date() + timedelta(days=2))
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date())

    if st.button("💾 СОХРАНИТЬ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        days_in_port = (datetime.now().date() - arrival_date).days
        overdue = max(0, days_in_port - allowed_days)
        demurrage_total = overdue * demurrage_rate
        
        # Расчет чистой прибыли
        net_profit = float(price_sell) - price_buy_usd - actual_freight - float(duties) - float(extra_costs) - demurrage_total
        # ШАГ 2: Чистая прибыль на 1 тонну
        profit_per_ton = float(net_profit / cargo_volume)
        
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Инкотермс': incoterms, 
            'Объем (Тонн)': cargo_volume, 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 'Цена закупки (вход)': float(price_buy_total), 'Валюта закупки': buy_curr, 
            'Цена продажи (USD)': float(price_sell), 'Фрахт ($)': float(freight), 'Пошлины и Страховка ($)': float(duties),
            'Прочие расходы ($)': float(extra_costs), 'Норма простоя (дн)': int(allowed_days), 'Ставка демереджа ($/сут)': float(demurrage_rate), 
            'Крайняя дата прибытия': str(deadline_date), 'Дата захода в порт': str(arrival_date), 'Демередж ($)': float(demurrage_total), 
            'Чистая прибыль ($)': float(net_profit), 'Прибыль/Тонна ($)': float(profit_per_ton)
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        
        tg_text = f"📝 *Новая сделка сохранена!*\n\n*ID:* {deal_id}\n*Груз:* {cargo_volume} Тонн\n*Прибыль:* ${net_profit:,.2f} USD\n*Маржа/Тонна:* ${profit_per_ton:,.2f}"
        try:
            url = f"https://telegram.org{tg_token.strip()}/sendMessage"
            requests.post(url, json={"chat_id": tg_chat.strip(), "text": tg_text, "parse_mode": "Markdown"}, timeout=5)
        except:
            pass
        st.success(f"✅ Сделка {deal_id} успешно внесена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр торговых сделок")
    
    # ШАГ 3: Быстрые фильтры над таблицей Excel
    status_filter = st.radio("Фильтр по статусу рейса:", ["Все сделки", "В пути", "В порту", "Завершена (Архив)"], horizontal=True)
    
    display_df = st.session_state.df_data
    if status_filter != "Все сделки" and 'Статус рейса' in display_df.columns:
        display_df = display_df[display_df['Статус рейса'] == status_filter]
        
    st.dataframe(display_df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        display_df.to_excel(writer, index=False, sheet_name='Сделки')
    st.download_button(label="📥 СКАЧАТЬ ВЫБРАННЫЙ РЕЕСТР В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="CCT1_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Умный Мониторинг & Логистический Радар")
    df = st.session_state.df_data
    
    # ШАГ 3: Радар показывает только те суда, которые сейчас активны («В пути» или «В порту»)
    radar_df = df
    if 'Статус рейса' in df.columns:
        radar_df = df[df['Статус рейса'] != "Завершена (Архив)"]
        
    if radar_df.empty:
        st.info("Нет активных рейсов («В пути» или «В порту») для мониторинга. Все сделки в архиве.")
        return
        
    selected_deal = st.selectbox("Выберите активное судно для слежения:", list(radar_df['ID Сделки'].unique()))
    v_rows = radar_df[radar_df['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        
        # ШАГ 2 + 3: Красивая сводка по объемам и статусу груза
        st.write(f"🚢 **Судно:** {v_info.get('Название судна', 'Alpha')} | **Объем:** {v_info.get('Объем (Тонн)', 5000)} Тонн | **Текущий статус:** {v_info.get('Статус рейса', 'В пути')}")
        
        with st.spinner("Связь со спутниками AIS..."):
            v_lat, v_lon, v_speed, status_text = get_live_vessel_data(v_info['MMSI/IMO'])
        st.info(f"📡 {status_text}")
        
        with st.spinner("Поиск координат порта разгрузки..."):
            p_lat, p_lon, p_name = get_port_coordinates(v_info['Порт разгрузки'])
            
        distance_to_port = haversine(v_lat, v_lon, p_lat, p_lon)
        st.write(f"📍 **Порт разгрузки:** {p_name}")
        st.write(f"📏 **Дистанция до причала:** {round(distance_to_port, 1)} км")
        
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
                    st.error(f"🚨 **РАДАР ФИКСИРУЕТ ОПОЗДАНИЕ!** Просрочка: {days_late} дн. Возможный демередж: **-${risk_cost:,}**")
                else:
                    st.success("✅ **В графике рейса:** Скорости хватает.")
        else:
            st.error("🎯 Судно находится внутри акватории порта назначения!")
            entry_date = datetime.strptime(str(v_info.get('Дата захода в порт', datetime.now().date())), "%Y-%m-%d").date()
            days_spent = (datetime.now().date() - entry_date).days
            overdue = max(0, days_spent - int(v_info['Норма простоя (дн)']))
            st.error(f"🚨 Начислено демереджа: **${overdue * float(v_info['Ставка демереджа ($/сут)']):,}**")

        map_df = pd.DataFrame([{'latitude': float(v_lat), 'longitude': float(v_lon)}, {'latitude': float(p_lat), 'longitude': float(p_lon)}])
        st.map(map_df, zoom=3)
