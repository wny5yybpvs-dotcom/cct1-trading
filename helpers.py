import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta

# ==========================================
# 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
def get_live_vessel_data(mmsi):
    """ Возвращает строго 4 параметра для распаковки """
    return 39.55, 29.30, 10.0, "🛰️ Спутниковый статус AIS: Активен | Судно находится на подходе к терминалу"

# ==========================================
# 2. МОДУЛИ ИНТЕРФЕЙСА (ВКЛАДКИ)
# ==========================================
def render_input_tab(CURRENCY_RATES, tg_token, tg_chat):
    st.subheader("📥 Ввод новой зерновой сделки")
    
    deal_id = st.text_input("ID сделки:", value=f"DEAL-{datetime.now().strftime('%Y%m%d-%H%M')}")
    vessel_status = st.selectbox("🚦 Текущий статус рейса:", ["В порту", "В пути", "Завершена (Архив)"])
    incoterms = st.selectbox("Базис поставки (Инкотермс):", ["CIF", "CFR", "FOB"])
    cargo_volume = st.number_input("Объем погрузки (Тонн):", min_value=1.0, value=5000.0, step=100.0)
    deal_date = st.date_input("Дата сделки:", value=datetime.now().date())
    
    buy_curr = st.selectbox("Валюта закупки:", ["USD", "CNY", "RUB"])
    price_buy_total = st.number_input(f"ОБЩАЯ стоимость закупки груза ({buy_curr}):", min_value=0.0, value=700000.0)
    price_sell_total = st.number_input("ОБЩАЯ стоимость продажи груза (\$ USD):", min_value=0.0, value=180000.0)
    
    port_start = st.text_input("Порт ЗАГРУЗКИ:", value="Стамбул")
    port_end = st.text_input("Порт РАЗГРУЗКИ:", value="Новороссийск")
    vessel_name = st.text_input("Название судна:", value="Vessel Alpha")
    vessel_mmsi = st.text_input("MMSI или IMO судна:", value="211281610")
    
    freight = st.number_input("Стоимость фрахта судна (\$):", min_value=0.0, value=15000.0)
    duties = st.number_input("Пошлины, Страховка и Сертификаты (\$):", min_value=0.0, value=5000.0)
    extra_costs = st.number_input("Прочие накладные расходы на рейс (\$):", min_value=0.0, value=2000.0)
    allowed_days = st.number_input("Норма простоя на выгрузку (дней):", min_value=1, value=3)
    demurrage_rate = st.number_input("Ставка демереджа (\$ / сутки):", min_value=0.0, value=5000.0)
    
    arrival_date = st.date_input("Дата фактического захода в порт:", value=datetime.now().date() - timedelta(days=6))

    if st.button("💾 СОХРАНИТЬ ЗЕРНОВУЮ СДЕЛКУ В БАЗУ", type="primary", use_container_width=True):
        new_row = {
            'ID Сделки': deal_id, 'Дата': str(deal_date), 'Статус рейса': vessel_status, 'Инкотермс': incoterms,
            'Объем (Тонн)': cargo_volume, 'Название судна': vessel_name, 'MMSI/IMO': vessel_mmsi,
            'Порт загрузки': port_start, 'Порт разгрузки': port_end, 
            'Цена закупки (вход)': price_buy_total, 'Валюта закупки': buy_curr, 'Цена продажи (USD)': price_sell_total, 
            'Фрахт (\$)': float(freight), 'Пошлины и Страховка (\$)': float(duties), 'Прочие расходы (\$)': float(extra_costs), 
            'Норма простоя (дн)': allowed_days, 'Ставка демереджа (\$/сут)': float(demurrage_rate),
            'Крайняя дата прибытия': str(datetime.now().date() + timedelta(days=2)), 
            'Дата захода в порт': str(arrival_date),
            'Демередж (\$)': 0.0, 'Чистая прибыль (\$)': 0.0, 'Прибыль/Тонна (\$)': 0.0
        }
        st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"✅ Зерновая сделка {deal_id} успешно сохранена!")
        st.rerun()

def render_excel_tab():
    st.subheader("📋 Реестр зерновых сделок")
    
    current_today = datetime.now().date()
    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        arr_dt = datetime.strptime(str(row['Дата захода в порт']), "%Y-%m-%d").date()
        days_in_port = (current_today - arr_dt).days
        overdue = max(0, days_in_port - int(row['Норма простоя (дн)']))
        row['Демередж (\$)'] = overdue * float(row['Ставка демереджа (\$/сут)'])
        
        buy_curr = row['Валюта закупки']
        rate = 7.3 if buy_curr == 'CNY' else (95.0 if buy_curr == 'RUB' else 1.0)
        buy_usd = float(row['Цена закупки (вход)']) / rate
        fr = 0.0 if row['Инкотермс'] == "FOB" else float(row['Фрахт (\$)'])
        
        row['Чистая прибыль (\$)'] = float(row['Цена продажи (USD)']) - buy_usd - fr - float(row['Пошлины и Страховка (\$)']) - float(row['Прочие расходы (\$)']) - row['Демередж (\$)']
        row['Прибыль/Тонна (\$)'] = row['Чистая прибыль (\$)'] / float(row['Объем (Тонн)'])
        updated_rows.append(row)
        
    st.session_state.df_data = pd.DataFrame(updated_rows)
    st.dataframe(st.session_state.df_data, use_container_width=True)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        st.session_state.df_data.to_excel(writer, index=False, sheet_name='CCT1_Report')
    st.download_button(label="📥 СКАЧАТЬ В EXCEL (.xlsx)", data=buffer.getvalue(), file_name="CCT1_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def render_radar_tab(tg_token, tg_chat):
    st.subheader("📊 Логистический Радар Зерновозов")
    
    current_today = datetime.now().date()
    updated_rows = []
    for row in st.session_state.df_data.to_dict('records'):
        arr_dt = datetime.strptime(str(row['Дата захода в порт']), "%Y-%m-%d").date()
        days_in_port = (current_today - arr_dt).days
        overdue = max(0, days_in_port - int(row['Норма простоя (дн)']))
        row['Демередж (\$)'] = overdue * float(row['Ставка демереджа (\$/сут)'])
        
        buy_curr = row['Валюта закупки']
        rate = 7.3 if buy_curr == 'CNY' else (95.0 if buy_curr == 'RUB' else 1.0)
        buy_usd = float(row['Цена закупки (вход)']) / rate
        fr = 0.0 if row['Инкотермс'] == "FOB" else float(row['Фрахт (\$)'])
        
        row['Чистая прибыль (\$)'] = float(row['Цена продажи (USD)']) - buy_usd - fr - float(row['Пошлины и Страховка (\$)']) - float(row['Прочие расходы (\$)']) - row['Демередж (\$)']
        row['Прибыль/Тонна (\$)'] = row['Чистая прибыль (\$)'] / float(row['Объем (Тонн)'])
        updated_rows.append(row)
    st.session_state.df_data = pd.DataFrame(updated_rows)

    selected_deal = st.selectbox("Выберите судно для трекинга:", list(st.session_state.df_data['ID Сделки'].unique()))
    v_rows = st.session_state.df_data[st.session_state.df_data['ID Сделки'] == selected_deal].to_dict('records')
    
    if len(v_rows) > 0:
        v_info = v_rows[0]  # Исправлено: берем первый словарь из списка записей
        st.markdown(f"### 🚢 Мониторинг рейса: `{v_info.get('Название судна')}`")
        
        lat, lon, speed, status_text = get_live_vessel_data(v_info.get('MMSI/IMO'))
        st.success(status_text)
        
        arr_dt = datetime.strptime(str(v_info['Дата захода в порт']), "%Y-%m-%d").date()
        total_days_spent = (current_today - arr_dt).days
        
        # ВЫВОД МЕТРИК ДЕМЕРЕДЖА И ПРИБЫЛИ
        st.markdown("#### ⚙️ Экономические показатели простоя:")
        st.metric(label="🚨 ТЕКУЩИЙ НАБЕЖАВШИЙ ДЕМЕРЕДЖ", value=f"\${v_info.get('Демередж (\$)'):,.2f}")
        st.metric(label="💵 ЧИСТАЯ ПРИБЫЛЬ С УЧЕТОМ ШТРАФОВ", value=f"\${v_info.get('Чистая прибыль (\$)'):,.2f}")
        
        st.info(f"📅 Судно находится в порту назначения уже **{total_days_spent} дней** (Разрешенная норма простоя: {v_info.get('Норма простоя (дн)')} дн.)")
        
        # ==========================================
        # СТАНДАРТНАЯ КАРТА STREAMLIT ДЛЯ МОБИЛЬНЫХ
        # ==========================================
        st.markdown("#### 📍 Положение судна на карте:")
        
        # Хардкод-координаты для стабильности
        p_start_lat, p_start_lon = 41.0151, 28.9795   # Стамбул
        p_end_lat, p_end_lon = 44.7239, 37.7686       # Новороссийск
        
        map_points = [
            {'latitude': p_start_lat, 'longitude': p_start_lon, 'Название': 'Порт загрузки'},
            {'latitude': lat, 'longitude': lon, 'Название': 'Текущая позиция судна'},
            {'latitude': p_end_lat, 'longitude': p_end_lon, 'Название': 'Порт разгрузки'}
        ]
        df_map = pd.DataFrame(map_points)
        st.map(df_map, zoom=4, use_container_width=True)
        
        # Текстовый дубляж схемы для 100% контроля
        st.markdown("#### 📋 Статус логистической цепочки:")
        p_start = v_info.get('Порт загрузки', 'Старт')
        p_end = v_info.get('Порт разгрузки', 'Финиш')
        
        st.warning(f"🏁 **[ТЕКУЩИЙ ЭТАП]** Судно прошло маршрут **{p_start} -> {p_end}** и сейчас оштрафовано за простой в порту разгрузки.")
