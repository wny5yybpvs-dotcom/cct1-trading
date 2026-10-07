import streamlit as st
import pandas as pd
import io
import datetime

# ==========================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def get_live_vessel_data(mmsi):
    return 39.55, 29.30, 10.0, "🛰️ Статус AIS: Активен | Судно пришвартовано под выгрузку grain терминала"

# ==========================================
# 2. МОДУЛИ ИНТЕРФЕЙСА (ВКЛАДКИ)
# ==========================================
def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("📥 Ввод зерновой сделки & Калькулятор Паритета")
    
    today_dt = datetime.date.today()
    default_laycan = today_dt + datetime.timedelta(days=2)
    default_arrival = today_dt - datetime.timedelta(days=6)
    
    col1, col2 = st.columns(2)
    with col1:
        deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}")
        vessel_status = st.selectbox("🚦 Статус рейса:", ["В порту", "В пути", "Завершена (Архив)"])
        incoterms = st.selectbox("Базис поставки:", ["CIF", "CFR", "FOB"])
        cargo_volume = st.number_input("Объем погрузки (Брутто Тонн):", min_value=1.0, value=5000.0, step=100.0)
    with col2:
        deal_date = st.date_input("Дата сделки:", value=today_dt)
        vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
        port_start = st.text_input("Порт ЗАГРУЗКИ:", value="Стамбул")
        port_end = st.text_input("Порт РАЗГРУЗКИ:", value="Новороссийск")

    st.subheader("🌾 Качество зерна (Расчет Рефакции веса)")
    moisture = st.number_input("Влажность фактическая (%)", min_value=0.0, max_value=30.0, value=14.5, step=0.1)
    admixture = st.number_input("Сорная примесь фактическая (%)", min_value=0.0, max_value=20.0, value=2.5, step=0.1)

    st.subheader("💵 Экономика & Ценовой Паритет (Netback)")
    buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
    price_buy_total = st.number_input(f"Фактическая цена закупки груза ({buy_curr}):", min_value=0.0, value=700000.0)
    price_sell_total = st.number_input("Цена продажи контракта ($ USD):", min_value=0.0, value=180000.0)
    target_margin_per_ton = st.number_input("Желаемая чистая маржа трейдера ($ / тонну):", min_value=0.0, value=10.0)

    st.subheader("🚢 Сталийное время, Фрахт & Пошлины")
    freight = st.number_input("Стоимость фрахта судна ($):", min_value=0.0, value=15000.0)
    duties = st.number_input("Экспортная пошлина ($):", min_value=0.0, value=0.0)
    extra_costs = st.number_input("Прочие расходы, анализы ГХС ($):", min_value=0.0, value=2000.0)
    discharge_rate = st.number_input("Контрактная норма выгрузки (Тонн / сутки):", min_value=1.0, value=1500.0)
    demurrage_rate = st.number_input("Ставка демереджа ($ / сутки):", min_value=0.0, value=5000.0)
    arrival_date = st.date_input("Дата фактического захода в порт:", value=default_arrival)

    if st.button("💾 СОХРАНИТЬ СДЕЛКУ ТРЕЙДЕРА В БАЗУ", type="primary", use_container_width=True):
        m_loss = float(max(0.0, (moisture - 14.0) / 100.0) * cargo_volume)
        a_loss = float(max(0.0, (admixture - 2.0) / 100.0) * cargo_volume)
        total_refaction = float(m_loss + a_loss)
        delivered_volume = float(cargo_volume - total_refaction)

        actual_freight = 0.0 if incoterms == "FOB" else float(freight)
        total_costs_before_grain = actual_freight + float(duties) + float(extra_costs)
        available_for_grain_usd = float(price_sell_total) - total_costs_before_grain - (target_margin_per_ton * cargo_volume)
        netback_cpt_usd_per_ton = available_for_grain_usd / cargo_volume

        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Indoterms': incoterms,
            'Объем (Тонн)': cargo_volume, 'Название судна': vessel_name, 'MMSI/IMO': "211281610",
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 
            'Цена закупки (вход)': price_buy_total, 'Валюта закупки': buy_curr, 'Цена продажи (USD)': price_sell_total, 
            'Фрахт ($)': actual_freight, 'Экспортная пошлина ($)': float(duties), 'Прочие расходы ($)': float(extra_costs), 
            'Норма выгрузки (т/сут)': discharge_rate, 'Ставка демереджа ($/сут)': float(demurrage_rate),
            'Крайняя дата прибытия': str(default_laycan), 
            'Дата захода в порт': str(arrival_date),
            'Влажность (%)': moisture, 'Сорная примесь (%)': admixture,
            'Рефакция веса (Тонн)': round(total_refaction, 1), 'Объем выгрузки (Тонн)': round(delivered_volume, 1),
            'Паритет закупки CPT ($/т)': round(netback_cpt_usd_per_ton, 2),
            'Демередж ($)': 0.0, 'Чистая прибыль ($)': 0.0, 'Прибыль/Тонна ($)': 0.0
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"✅ Сделка зернотрейдера {deal_id} успешно сохранена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр торговых сделок")
    current_today = datetime.date.today()
    
    if not st.session_state.df_data.empty:
        if 'Объем погрузки (Тонн)' in st.session_state.df_data.columns:
            st.session_state.df_data = st.session_state.df_data.rename(columns={'Объем погрузки (Тонн)': 'Объем (Тонн)'})

    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        cargo = float(row.get('Объем (Тонн)', 5000.0))
        rate_per_day = float(row.get('Норма выгрузки (т/сут)', 1500.0))
        allowed_laydays = cargo / max(1.0, rate_per_day)
        
        try:
            arr_dt = datetime.datetime.strptime(str(row.get('Дата захода в порт', current_today)), "%Y-%m-%d").date()
        except:
            arr_dt = current_today
            
        days_in_port = (current_today - arr_dt).days
        overdue = max(0.0, float(days_in_port) - allowed_laydays)
        row['Демередж ($)'] = overdue * float(row.get('Ставка демереджа ($/сут)', 0.0))
        
        buy_curr = row.get('Валюта закупки', 'CNY')
        curr_rate = 7.3 if buy_curr == 'CNY' else (95.0 if buy_curr == 'RUB' else 1.0)
        buy_usd = float(row.get('Цена закупки (вход)', 0.0)) / curr_rate
        fr = 0.0 if row.get('Инкотермс') == "FOB" else float(row.get('Фрахт ($)', 0.0))
        
        row['Чистая прибыль ($)'] = float(row.get('Цена продажи (USD)', 0.0)) - buy_usd - fr - float(row.get('Экспортная пошлина ($)', 0.0)) - float(row.get('Прочие расходы ($)', 0.0)) - row['Демередж ($)']
        row['Прибыль/Тонна ($)'] = row['Чистая прибыль ($)'] / max(1.0, cargo)
        updated_rows.append(row)
        
    st.session_state.df_data = pd.DataFrame(updated_rows)

    if not st.session_state.df_data.empty and 'Название судна' in st.session_state.df_data.columns:
        st.markdown("#### 📈 График PnL сделок ($)")
        chart_df = st.session_state.df_data[['Название судна', 'Чистая прибыль ($)', 'Демередж ($)']].set_index('Название судна')
        st.bar_chart(chart_df)

    st.dataframe(st.session_state.df_data, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.df_data.to_excel(writer, index=False, sheet_name='Trading_Report')
    st.download_button(label="📥 СКАЧАТЬ В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="Grain_Trading_Report.xlsx", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Логистический Радар Зерновозов")
    current_today = datetime.date.today()
    
    if 'Объем погрузки (Тонн)' in st.session_state.df_data.columns:
        st.session_state.df_data = st.session_state.df_data.rename(columns={'Объем погрузки (Тонн)': 'Объем (Тонн)'})

    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        cargo = float(row.get('Объем (Тонн)', 5000.0))
        rate_per_day = float(row.get('Норма выгрузки (т/сут)', 1500.0))
        allowed_laydays = cargo / max(1.0, rate_per_day)
        
        try:
            arr_dt = datetime.datetime.strptime(str(row.get('Дата захода в порт', current_today)), "%Y-%m-%d").date()
        except:
            arr_dt = current_today
            
        days_in_port = (current_today - arr_dt).days
        overdue = max(0.0, float(days_in_port) - allowed_laydays)
        row['Демередж ($)'] = overdue * float(row.get('Ставка демереджа ($/сут)', 0.0))
        
        buy_curr = row.get('Валюта закупки', 'CNY')
        curr_rate = 7.3 if buy_curr == 'CNY' else (95.0 if buy_curr == 'RUB' else 1.0)
        buy_usd = float(row.get('Цена закупки (вход)', 0.0)) / curr_rate
        fr = 0.0 if row.get('Инкотермс') == "FOB" else float(row.get('Фрахт ($)', 0.0))
        
        row['Чистая прибыль ($)'] = float(row.get('Цена продажи (USD)', 0.0)) - buy_usd - fr - float(row.get('Экспортная пошлина ($)', 0.0)) - float(row.get('Прочие расходы ($)', 0.0)) - row['Демередж ($)']
        row['Прибыль/Тонна ($)'] = row['Чистая прибыль ($)'] / max(1.0, cargo)
        updated_rows.append(row)
    st.session_state.df_data = pd.DataFrame(updated_rows)

    if st.session_state.df_data.empty:
        st.info("Нет активных сделок.")
        return

    selected_deal = st.selectbox("Выберите судно для трекинга:", list(st.session_state.df_data['ID Сделки'].unique()))
    v_rows = st.session_state.df_data[st.session_state.df_data['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]
        
        try:
            st.markdown(f"### 🚢 Оперативный трекинг: `{v_info.get('Название судна', 'Alpha')}`")
            
            lat, lon, speed, status_text = get_live_vessel_data(v_info.get('MMSI/IMO'))
            st.success(status_text)
            
            cargo = float(v_info.get('Объем (Тонн)', 5000.0))
            rate_per_day = float(v_info.get('Норма выгрузки (т/сут)', 1500.0))
            allowed_days = round(cargo / max(1.0, rate_per_day), 1)
            
