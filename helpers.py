import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timedelta

# ==========================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (ОФФЛАЙН ДАННЫЕ)
# ==========================================
def get_port_coordinates(port_name):
    """ Оффлайн-геокодер для защиты от блокировок карт """
    name_clean = str(port_name).lower()
    if "стамбул" in name_clean or "istanbul" in name_clean:
        return 41.0151, 28.9795
    if "новороссийск" in name_clean or "novorossiysk" in name_clean:
        return 44.7239, 37.7686
    return 44.7239, 37.7686  # Дефолт: Новороссийск

def get_live_vessel_data(mmsi):
    """ Оффлайн-координаты судна для стабильного рендеринга """
    return 39.55, 29.30, "🚢 Судно в пути (Эгейское море) | Скорость: 10.0 узлов"

# ==========================================
# 2. МОДУЛИ ИНТЕРФЕЙСА (ВКЛАДКИ)
# ==========================================
def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("🌾 Параметры зернового груза")
    
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    vessel_status = st.selectbox("🚦 Текущий статус рейса:", ["В пути", "В порту", "Завершена (Архив)"])
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    cargo_volume = st.number_input("Объем погрузки (Тонн):", min_value=1.0, value=5000.0, step=100.0)
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    
    st.subheader("💵 Экономика зерновой сделки")
    buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
    price_buy_total = st.number_input(f"ОБЩАЯ стоимость закупки груза ({buy_curr}):", min_value=0.0, value=700000.0)
    price_sell_total = st.number_input("ОБЩАЯ стоимость продажи груза ($ USD):", min_value=0.0, value=180000.0)
    
    st.subheader("🚢 Логистика, Сроки и Накладные расходы")
    port_start = st.text_input("Порт ЗАГРУЗКИ:", value="Стамбул")
    port_end = st.text_input("Порт РАЗГРУЗКИ:", value="Новороссийск")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    
    freight = st.number_input("Стоимость фрахта судна ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины, Страховка и Сертификаты ($):", min_value=0.0, value=5000.0)
    extra_costs = st.number_input("Прочие накладные расходы на рейс ($):", min_value=0.0, value=2000.0)
    allowed_days = st.number_input("Норма простоя на выгрузку (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    
    deadline_date = st.date_input("Крайняя дата прибытия (Laycan):", value=datetime.now().date() + timedelta(days=2))
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date() - timedelta(days=6))

    if st.button("💾 СОХРАНИТЬ ЗЕРНОВУЮ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        buy_usd_total = float(price_buy_total / CURRENCY_RATES.get(buy_curr, 1.0))
        
        current_today = datetime.now().date()
        days_in_port = (current_today - arrival_date).days
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
        st.success(f"✅ Зерновая сделка {deal_id} успешно сохранена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр зерновых сделок")
    
    current_today = datetime.now().date()
    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        if row.get('Статус рейса') == "В порту":
            arr_dt = datetime.strptime(str(row['Дата захода в порт']), "%Y-%m-%d").date()
            days_in_port = (current_today - arr_dt).days
            overdue = max(0, days_in_port - int(row['Норма простоя (дн)']))
            row['Демередж ($)'] = overdue * float(row['Ставка демереджа ($/сут)'])
            
            buy_usd = float(row['Цена закупки (вход)']) / 7.2 if row['Валюта закупки'] == 'CNY' else (float(row['Цена закупки (вход)']) / 93.5 if row['Валюта закупки'] == 'RUB' else float(row['Цена закупки (вход)']))
            fr = 0.0 if row['Инкотермс'] == "FOB" else float(row['Фрахт ($)'])
            row['Чистая прибыль ($)'] = float(row['Цена продажи (USD)']) - buy_usd - fr - float(row['Пошлины и Страховка ($)']) - float(row['Прочие расходы ($)']) - row['Демередж ($)']
            row['Прибыль/Тонна ($)'] = row['Чистая прибыль ($)'] / float(row['Объем (Тонн)'])
        updated_rows.append(row)
    st.session_state.df_data = pd.DataFrame(updated_rows)

    status_filter = st.radio("Фильтр по статусу рейса:", ["Все сделки", "В пути", "В порту", "Завершена (Архив)"], horizontal=True)
    display_df = st.session_state.df_data
    if status_filter != "Все сделки":
        display_df = display_df[display_df['Статус рейса'] == status_filter]
        
    st.dataframe(display_df, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        display_df.to_excel(writer, index=False, sheet_name='CCT1_Trading')
    st.download_button(label="📥 СКАЧАТЬ РЕЕСТР В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="CCT1_Global_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Логистический Радар Зерновозов")
    
    current_today = datetime.now().date()
    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        if row.get('Статус рейса') == "В порту":
            arr_dt = datetime.strptime(str(row['Дата захода в порт']), "%Y-%m-%d").date()
            days_in_port = (current_today - arr_dt).days
            overdue = max(0, days_in_port - int(row['Норма простоя (дн)']))
            row['Демередж ($)'] = overdue * float(row['Ставка демереджа ($/сут)'])
        updated_rows.append(row)
    st.session_state.df_data = pd.DataFrame(updated_rows)

    df = st.session_state.df_data
    radar_df = df[df['Статус рейса'] != "Завершена (Архив)"] if 'Статус рейса' in df.columns else df
        
    if radar_df.empty:
        st.info("Нет активных зерновозов на мониторинге.")
        return
        
    selected_deal = st.selectbox("Выберите судно для трекинга:", list(radar_df['ID Сделки'].unique()))
    v_rows = radar_df[radar_df['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        # ИСПРАВЛЕНО: берём первый элемент списка строк, чтобы код не падал!
        v_info = v_rows[0] 
        st.markdown(f"### 🚢 Мониторинг судна: `{v_info.get('Название судна', 'Alpha')}`")
        
        v_lat, v_lon, status_text = get_live_vessel_data(v_info.get('MMSI/IMO'))
        p_start_lat, p_start_lon = get_port_coordinates(v_info.get('Порт загрузки', 'Стамбул'))
        p_end_lat, p_end_lon = get_port_coordinates(v_info.get('Порт разгрузки', 'Новороссийск'))
        
        st.success(status_text)
        
        arr_dt = datetime.strptime(str(v_info['Дата захода в порт']), "%Y-%m-%d").date()
        total_days_spent = (current_today - arr_dt).days
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Фактически дней в порту", f"{total_days_spent} из {v_info.get('Норма простоя (дн)')} дн.")
            st.metric("Текущий демередж сделки", f"${v_info.get('Демередж ($)', 0.0):,.2f}")
        with col_m2:
            st.metric("Текущая чистая прибыль", f"${v_info.get('Чистая прибыль ($)', 0.0):,.2f}")
        
        # ==========================================
        # ЧИСТАЯ, НАДЁЖНАЯ СТАНДАРТНАЯ КАРТА STREAMLIT
        # ==========================================
        st.markdown("**📍 Нативная карта расположения судна и портов рейса:**")
        
        # Собираем точки маршрута в стандартную таблицу
        map_points = [
            {'latitude': p_start_lat, 'longitude': p_start_lon, 'Название': 'Порт загрузки'},
            {'latitude': v_lat, 'longitude': v_lon, 'Название': 'Текущая позиция судна'},
            {'latitude': p_end_lat, 'longitude': p_end_lon, 'Название': 'Порт разгрузки'}
        ]
        df_map = pd.DataFrame(map_points)
        
        # Вызываем стандартный, оптимизированный под телефоны st.map
        st.map(df_map, zoom=4, use_container_width=True)
        
        # Текстовый дубляж схемы для 100% контроля
        st.markdown("**📋 Схема этапа рейса:**")
        p_start = v_info.get('Порт загрузки', 'Старт')
